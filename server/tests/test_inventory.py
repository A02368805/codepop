from decimal import Decimal

from apps.inventory.models import LocalSupplier, SupplierReplenishment, SupplySchedule
from apps.inventory.services import (
    InventoryServiceError,
    approve_supply_schedule,
    approve_transfer,
    create_supplier_replenishment_order,
    create_transfer_request,
    deliver_transfer,
    determine_transfer_scope,
    get_hub_balance,
    get_store_balance,
    receive_supplier_replenishment,
    receive_transfer,
    request_transfer,
    reserve_transfer_inventory,
    ship_transfer,
)
from apps.supply_hubs.models import SupplyTransfer
from django.test import TestCase

from .helpers import (
    assign_region,
    assign_store,
    make_hub,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


class InventoryWorkflowTests(TestCase):
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

        cls.store_c1 = make_store(
            store_code="C001", region=cls.region_c, name="Logan Main"
        )
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

        cls.hub_g = make_hub(
            hub_code="HUB-G",
            region=cls.region_g,
            name="Boise Hub",
            city="Boise",
            state_code="ID",
            latitude="43.615021",
            longitude="-116.202316",
        )
        cls.hub_a = make_hub(
            hub_code="HUB-A",
            region=cls.region_a,
            name="Chicago Hub",
            city="Chicago",
            state_code="IL",
            latitude="41.878113",
            longitude="-87.629799",
        )

        cls.manager = make_user(
            email="manager@test.local",
            role="manager",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.logistics = make_user(
            email="logistics@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.super_admin = make_user(
            email="super@test.local",
            role="super_admin",
            default_region=cls.region_c,
            is_superuser=True,
        )
        assign_store(cls.manager, cls.store_c1)
        assign_region(cls.logistics, cls.region_c)

        cls.inventory_item = make_inventory_item(
            sku="SYRUP-VANILLA", name="Vanilla Syrup"
        )
        cls.cup_item = make_inventory_item(
            sku="CUPS-24OZ",
            name="24oz Cups",
            category="cups",
            threshold="100.00",
        )
        cls.local_supplier = LocalSupplier.objects.create(
            name="Cache Valley Vendor",
            service_region=cls.region_c,
            contact_name="Morgan Supply",
            email="vendor@test.local",
            phone_number="8015550133",
            item_categories_json=["syrup", "cups"],
            is_active=True,
        )

        source_balance = get_store_balance(cls.store_c1, cls.inventory_item)
        source_balance.on_hand_quantity = Decimal("20.00")
        source_balance.reorder_threshold = Decimal("5.00")
        source_balance.save()

        destination_balance = get_store_balance(cls.store_c2, cls.inventory_item)
        destination_balance.on_hand_quantity = Decimal("4.00")
        destination_balance.reorder_threshold = Decimal("5.00")
        destination_balance.save()

        hub_balance = get_hub_balance(cls.hub_g, cls.cup_item)
        hub_balance.on_hand_quantity = Decimal("500.00")
        hub_balance.save()

    def test_auto_transfer_request_selects_best_same_region_source(self):
        transfer = create_transfer_request(
            actor=self.logistics,
            destination_store=self.store_c2,
            inventory_item=self.inventory_item,
            quantity_requested=Decimal("3.00"),
            source_kind="auto",
            notes="auto route test",
        )

        self.assertEqual(transfer.source_store, self.store_c1)
        self.assertIsNone(transfer.source_hub)
        self.assertIn("same-region store stock", transfer.notes)

    def test_same_region_transfer_moves_inventory_through_workflow(self):
        transfer = request_transfer(
            requested_by=self.manager,
            source_store=self.store_c1,
            destination_store=self.store_c2,
            line_items=[
                {
                    "inventory_item": self.inventory_item,
                    "quantity_requested": Decimal("5.00"),
                }
            ],
            notes="test same-region transfer",
            is_ai_draft=True,
        )

        self.assertEqual(
            transfer.transfer_scope, SupplyTransfer.TransferScope.SAME_REGION_STORE
        )
        self.assertTrue(transfer.is_ai_draft)

        approve_transfer(transfer, approver=self.logistics)
        reserve_transfer_inventory(transfer)
        ship_transfer(transfer)
        deliver_transfer(transfer)
        receive_transfer(transfer, actor=self.manager)
        transfer.refresh_from_db()

        source_balance = get_store_balance(self.store_c1, self.inventory_item)
        destination_balance = get_store_balance(self.store_c2, self.inventory_item)
        self.assertEqual(transfer.status, SupplyTransfer.Status.RECEIVED)
        self.assertEqual(source_balance.on_hand_quantity, Decimal("15.00"))
        self.assertEqual(destination_balance.on_hand_quantity, Decimal("9.00"))

    def test_direct_cross_region_store_transfer_is_rejected(self):
        with self.assertRaises(InventoryServiceError):
            request_transfer(
                requested_by=self.manager,
                source_store=self.store_c1,
                destination_store=self.store_g1,
                line_items=[
                    {
                        "inventory_item": self.inventory_item,
                        "quantity_requested": Decimal("1.00"),
                    }
                ],
                notes="invalid cross-region store transfer",
            )

    def test_hub_distance_eligibility_uses_1000_mile_rule(self):
        scope, distance = determine_transfer_scope(
            source_hub=self.hub_g,
            destination_store=self.store_c1,
        )
        self.assertEqual(scope, SupplyTransfer.TransferScope.CROSS_REGION_HUB)
        self.assertLess(distance, Decimal("1000"))

        with self.assertRaises(InventoryServiceError):
            determine_transfer_scope(
                source_hub=self.hub_a, destination_store=self.store_c1
            )

    def test_ai_supply_schedules_require_logistics_or_super_admin_approval(self):
        schedule = SupplySchedule.objects.create(
            store=self.store_c1,
            inventory_item=self.inventory_item,
            recommended_source_type=SupplySchedule.RecommendedSourceType.HUB,
            recommended_source_reference={"region_code": "C"},
            recommended_quantity=Decimal("12.00"),
            recommended_frequency_days=7,
            created_by_ai=True,
        )
        with self.assertRaises(InventoryServiceError):
            approve_supply_schedule(schedule, approver=self.manager)

        approve_supply_schedule(schedule, approver=self.logistics)
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, SupplySchedule.Status.APPROVED)
        self.assertEqual(schedule.approved_by, self.logistics)

    def test_supplier_replenishment_order_receipt_updates_inventory(self):
        store_balance = get_store_balance(self.store_c1, self.cup_item)
        store_balance.on_hand_quantity = Decimal("25.00")
        store_balance.reorder_threshold = Decimal("100.00")
        store_balance.save()

        replenishment = create_supplier_replenishment_order(
            actor=self.logistics,
            supplier=self.local_supplier,
            store=self.store_c1,
            inventory_item=self.cup_item,
            quantity_requested=Decimal("80.00"),
            notes="cups for the weekend rush",
        )
        self.assertEqual(replenishment.status, SupplierReplenishment.Status.ORDERED)
        self.assertEqual(replenishment.quantity_requested, Decimal("250"))

        receive_supplier_replenishment(replenishment, actor=self.logistics)
        replenishment.refresh_from_db()
        store_balance.refresh_from_db()

        self.assertEqual(replenishment.status, SupplierReplenishment.Status.RECEIVED)
        self.assertEqual(replenishment.quantity_received, Decimal("250"))
        self.assertEqual(store_balance.on_hand_quantity, Decimal("275.00"))

    def test_transfer_approval_cannot_exceed_requested_quantity(self):
        transfer = request_transfer(
            requested_by=self.manager,
            source_store=self.store_c1,
            destination_store=self.store_c2,
            line_items=[
                {
                    "inventory_item": self.inventory_item,
                    "quantity_requested": Decimal("2.00"),
                }
            ],
            notes="approval bounds test",
        )

        with self.assertRaises(InventoryServiceError):
            approve_transfer(
                transfer,
                approver=self.logistics,
                approved_quantities={
                    str(self.inventory_item.id): Decimal("3.00"),
                },
            )

    def test_transfer_receive_rejects_quantity_above_approved(self):
        transfer = request_transfer(
            requested_by=self.manager,
            source_store=self.store_c1,
            destination_store=self.store_c2,
            line_items=[
                {
                    "inventory_item": self.inventory_item,
                    "quantity_requested": Decimal("2.00"),
                }
            ],
            notes="receive bounds test",
        )

        approve_transfer(
            transfer,
            approver=self.logistics,
            approved_quantities={
                str(self.inventory_item.id): Decimal("2.00"),
            },
        )
        reserve_transfer_inventory(transfer)
        ship_transfer(transfer)
        deliver_transfer(transfer)

        line_item = transfer.line_items.first()
        line_item.quantity_received = Decimal("3.00")
        line_item.save(update_fields=["quantity_received"])

        with self.assertRaises(InventoryServiceError):
            receive_transfer(transfer, actor=self.manager)
