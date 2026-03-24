from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import get_store_balance
from apps.orders.models import Order
from apps.orders.services import RefundEligibilityError, create_order, ensure_refund_allowed, transition_order_status
from apps.payments.models import PaymentTransaction, RevenueLedgerEntry
from apps.payments.services import record_payment_pending, record_payment_success, record_refund

from .helpers import make_inventory_item, make_region, make_store, make_user


class OrderWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.inventory_item = make_inventory_item(sku="SYRUP-STRAWBERRY")
        cls.cups = make_inventory_item(
            sku="CUPS-24OZ",
            name="24oz Cups",
            category="cups",
            threshold="100.00",
        )

        balance = get_store_balance(cls.store, cls.inventory_item)
        balance.on_hand_quantity = Decimal("12.00")
        balance.reorder_threshold = Decimal("4.00")
        balance.save()

        cup_balance = get_store_balance(cls.store, cls.cups)
        cup_balance.on_hand_quantity = Decimal("200.00")
        cup_balance.reorder_threshold = Decimal("50.00")
        cup_balance.save()

    def _create_order(self):
        return create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "large",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("1.00"),
                    "quantity": 2,
                    "customizations": {
                        "extras_total": "1.00",
                        "inventory_requirements": [
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "2.00"},
                            {"sku": "CUPS-24OZ", "quantity": "2.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )

    def test_order_lifecycle_reserves_inventory_and_sets_timestamps(self):
        order = self._create_order()
        self.assertEqual(order.status, Order.Status.PRICING_VALIDATED)

        record_payment_pending(order, payment_intent_id="pi_test_001")
        self.assertEqual(order.payment_transaction.status, PaymentTransaction.Status.PENDING)

        record_payment_success(order, payment_intent_id="pi_test_001", actor=self.customer)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(order=order, entry_type=RevenueLedgerEntry.EntryType.SALE).count(),
            1,
        )

        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)
        transition_order_status(order, Order.Status.READY, actor=self.customer)
        transition_order_status(order, Order.Status.PICKED_UP, actor=self.customer)
        order.refresh_from_db()

        syrup_balance = get_store_balance(self.store, self.inventory_item)
        cup_balance = get_store_balance(self.store, self.cups)
        self.assertEqual(syrup_balance.on_hand_quantity, Decimal("10.00"))
        self.assertEqual(cup_balance.on_hand_quantity, Decimal("198.00"))
        self.assertEqual(order.status, Order.Status.PICKED_UP)
        self.assertIsNotNone(order.queued_at)
        self.assertIsNotNone(order.preparing_at)
        self.assertIsNotNone(order.ready_at)
        self.assertIsNotNone(order.picked_up_at)

    def test_refund_cutoff_blocks_customers_after_preparing(self):
        order = self._create_order()
        record_payment_pending(order, payment_intent_id="pi_test_002")
        record_payment_success(order, payment_intent_id="pi_test_002", actor=self.customer)
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        with self.assertRaises(RefundEligibilityError):
            ensure_refund_allowed(order, actor=self.customer)

    def test_privileged_refund_override_allows_refund_after_preparing(self):
        order = self._create_order()
        record_payment_pending(order, payment_intent_id="pi_test_003")
        record_payment_success(order, payment_intent_id="pi_test_003", actor=self.customer)
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        payment = record_refund(order, actor=self.admin, notes="Admin override for store issue.")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(order.refund_status, Order.RefundStatus.REFUNDED)
        self.assertEqual(payment.status, PaymentTransaction.Status.REFUNDED)
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(order=order, entry_type=RevenueLedgerEntry.EntryType.REFUND).count(),
            1,
        )
