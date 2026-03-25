from decimal import Decimal
from pathlib import Path

from apps.analytics.tasks import refresh_account_recommendations
from apps.imports.models import ImportJob
from apps.imports.services import CSVImportError, import_repair_status_csv, import_supply_usage_csv
from apps.inventory.models import SupplyUsageRecord
from apps.inventory.services import InventoryServiceError, determine_transfer_scope, get_store_balance
from apps.maintenance.models import MachineStatusEvent
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.orders.services import create_order, transition_order_status
from apps.payments.services import initialize_order_checkout
from apps.sync.models import AuditLog
from django.test import TestCase, override_settings

from .helpers import (
    assign_region,
    assign_store,
    make_hub,
    make_inventory_item,
    make_machine_type,
    make_region,
    make_store,
    make_user,
)


class Group2ExitGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region_c = make_region(code="C", name="Logan, UT")
        cls.region_g = make_region(
            code="G",
            name="Boise, ID",
            hub_city="Boise",
            hub_state_code="ID",
            latitude="43.615021",
            longitude="-116.202316",
        )
        cls.region_a = make_region(
            code="A",
            name="Chicago, IL",
            hub_city="Chicago",
            hub_state_code="IL",
            latitude="41.878113",
            longitude="-87.629799",
        )

        cls.store_c1 = make_store(store_code="C001", region=cls.region_c, name="Logan Main")
        cls.store_c2 = make_store(
            store_code="C002",
            region=cls.region_c,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.store_g1 = make_store(
            store_code="G001",
            region=cls.region_g,
            name="Boise Capitol",
            city="Boise",
            state_code="ID",
            address_line_1="50 Idaho St",
            postal_code="83702",
            latitude="43.615018",
            longitude="-116.202313",
        )

        cls.customer = make_user(
            email="gate-customer@test.local",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.logistics = make_user(
            email="gate-logistics@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.repair = make_user(
            email="gate-repair@test.local",
            role="repair_staff",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )

        assign_region(cls.logistics, cls.region_c)
        assign_store(cls.repair, cls.store_c1)

        cls.inventory_item = make_inventory_item(sku="SYRUP-GATE", name="Gate Syrup")
        cls.machine_type = make_machine_type(code="MIXER_GATE")

    @override_settings(PAYMENT_MODE="mock")
    def test_checkout_end_to_end_dev_mode_creates_payment_and_queues_order(self):
        order = create_order(
            store=self.store_c1,
            customer=self.customer,
            items=[
                {
                    "display_name": "Gate Drink",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.25"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.25",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=self.customer,
        )

        initialize_order_checkout(order, request=object(), actor=self.customer)
        order.refresh_from_db()

        self.assertEqual(order.status, Order.Status.QUEUED)
        self.assertTrue(hasattr(order, "payment_transaction"))
        self.assertEqual(order.payment_transaction.order_id, order.id)

    def test_inventory_cannot_go_negative_on_queue_transition(self):
        balance = get_store_balance(self.store_c1, self.inventory_item)
        balance.on_hand_quantity = Decimal("0.00")
        balance.reorder_threshold = Decimal("0.00")
        balance.save()

        order = create_order(
            store=self.store_c1,
            customer=self.customer,
            items=[
                {
                    "display_name": "Gate Syrup Drink",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [
                            {"sku": "SYRUP-GATE", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )
        transition_order_status(order, Order.Status.PAYMENT_PENDING, actor=self.customer)
        transition_order_status(order, Order.Status.PAID, actor=self.customer)

        with self.assertRaises(InventoryServiceError):
            transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        balance.refresh_from_db()
        self.assertEqual(balance.on_hand_quantity, Decimal("0.00"))

    def test_transfer_rules_same_region_and_1000_mile_hub_limits_are_enforced(self):
        with self.assertRaises(InventoryServiceError):
            determine_transfer_scope(
                source_store=self.store_c1,
                destination_store=self.store_g1,
            )

        far_hub = make_hub(
            hub_code="HUB-A",
            region=self.region_a,
            name="Chicago Hub",
            city="Chicago",
            state_code="IL",
            latitude="41.878113",
            longitude="-87.629799",
        )
        with self.assertRaises(InventoryServiceError):
            determine_transfer_scope(
                source_hub=far_hub,
                destination_store=self.store_c1,
            )

    def test_supply_and_repair_csv_failures_remain_transactional_and_auditable(self):
        bad_supply_csv = "\n".join(
            [
                "store_code,inventory_sku,usage_date,quantity_used",
                "C001,SYRUP-GATE,2026-03-18,2.00",
                "G001,SYRUP-GATE,2026-03-18,1.00",
            ]
        )
        with self.assertRaises(CSVImportError):
            import_supply_usage_csv(
                bad_supply_csv,
                uploaded_by=self.logistics,
                original_filename="gate-bad-supply.csv",
            )

        bad_repair_csv = "\n".join(
            [
                "store_address,machine_type_code,machine_operational_from_date,machine_status,status_date",
                "123 Main St Logan UT,MIXER_GATE,2025-07-01,warning,2026-03-18",
            ]
        )
        with self.assertRaises(CSVImportError):
            import_repair_status_csv(
                bad_repair_csv,
                uploaded_by=self.repair,
                original_filename="gate-bad-repair.csv",
                allow_machine_create=False,
            )

        self.assertEqual(SupplyUsageRecord.objects.count(), 0)
        self.assertEqual(MachineStatusEvent.objects.count(), 0)
        self.assertTrue(
            ImportJob.objects.filter(
                original_filename="gate-bad-supply.csv",
                status=ImportJob.Status.FAILED,
            ).exists()
        )
        self.assertTrue(
            ImportJob.objects.filter(
                original_filename="gate-bad-repair.csv",
                status=ImportJob.Status.FAILED,
            ).exists()
        )
        self.assertGreaterEqual(
            AuditLog.objects.filter(action="import.failed").count(),
            2,
        )

    def test_background_business_job_processes_recommendation_notification(self):
        result = refresh_account_recommendations(
            str(self.customer.id),
            reason="Group 2 gate",
        )

        self.assertIsNotNone(result)
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer,
                title="Fresh drink ideas",
            ).exists()
        )

    def test_canonical_route_file_has_no_legacy_endpoint_includes(self):
        urlconf_path = Path(__file__).resolve().parents[1] / "config" / "urls.py"
        urlconf_source = urlconf_path.read_text(encoding="utf-8")

        self.assertNotIn("codepop_backend", urlconf_source)
