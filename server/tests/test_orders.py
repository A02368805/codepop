import threading
from decimal import Decimal

from apps.inventory.services import InventoryServiceError, get_store_balance
from apps.orders.models import Order
from apps.orders.services import (
    OrderServiceError,
    RefundEligibilityError,
    create_order,
    ensure_refund_allowed,
    transition_order_status,
)
from apps.payments.models import PaymentTransaction, RevenueLedgerEntry
from apps.payments.services import (
    record_payment_pending,
    record_payment_success,
    record_refund,
)
from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase

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
        self.assertEqual(
            order.payment_transaction.status, PaymentTransaction.Status.PENDING
        )

        record_payment_success(
            order, payment_intent_id="pi_test_001", actor=self.customer
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(
                order=order, entry_type=RevenueLedgerEntry.EntryType.SALE
            ).count(),
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
        record_payment_success(
            order, payment_intent_id="pi_test_002", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        with self.assertRaises(RefundEligibilityError):
            ensure_refund_allowed(order, actor=self.customer)

    def test_privileged_refund_override_allows_refund_after_preparing(self):
        order = self._create_order()
        record_payment_pending(order, payment_intent_id="pi_test_003")
        record_payment_success(
            order, payment_intent_id="pi_test_003", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        payment = record_refund(
            order, actor=self.admin, notes="Admin override for store issue."
        )
        order.refresh_from_db()
        syrup_balance = get_store_balance(self.store, self.inventory_item)
        cup_balance = get_store_balance(self.store, self.cups)
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(order.refund_status, Order.RefundStatus.REFUNDED)
        self.assertEqual(payment.status, PaymentTransaction.Status.REFUNDED)
        self.assertEqual(syrup_balance.on_hand_quantity, Decimal("12.00"))
        self.assertEqual(cup_balance.on_hand_quantity, Decimal("200.00"))
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(
                order=order, entry_type=RevenueLedgerEntry.EntryType.REFUND
            ).count(),
            1,
        )

    def test_queue_transition_blocks_when_inventory_is_insufficient(self):
        order = self._create_order()
        balance = get_store_balance(self.store, self.inventory_item)
        balance.on_hand_quantity = Decimal("1.00")
        balance.save(update_fields=["on_hand_quantity", "updated_at"])

        record_payment_pending(order, payment_intent_id="pi_test_004")
        record_payment_success(
            order, payment_intent_id="pi_test_004", actor=self.customer
        )

        with self.assertRaises(InventoryServiceError):
            transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)

    def test_create_order_rejects_items_from_different_store_snapshot(self):
        with self.assertRaises(OrderServiceError):
            create_order(
                store=self.store,
                customer=self.customer,
                items=[
                    {
                        "display_name": "Berry Burst",
                        "size": "large",
                        "base_price": Decimal("5.50"),
                        "extras_total": Decimal("1.00"),
                        "quantity": 1,
                        "store_code_snapshot": "OTHER-STORE",
                        "customizations": {
                            "extras_total": "1.00",
                            "inventory_requirements": [],
                        },
                    }
                ],
                actor=self.customer,
            )


class InventoryConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.region = make_region(code="C", name="Logan, UT")
        self.store = make_store(
            store_code="C001",
            region=self.region,
            name="Logan Main",
        )
        self.customer = make_user(
            email="concurrency@test.local",
            preferred_store=self.store,
            default_region=self.region,
        )
        self.inventory_item = make_inventory_item(sku="SYRUP-STRAWBERRY")

        balance = get_store_balance(self.store, self.inventory_item)
        balance.on_hand_quantity = Decimal("1.00")
        balance.reorder_threshold = Decimal("0.25")
        balance.save()

    def _create_paid_order(self):
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "large",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("1.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "1.00",
                        "inventory_requirements": [
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )
        record_payment_pending(order, payment_intent_id=f"pi_{order.public_order_code}")
        record_payment_success(
            order,
            payment_intent_id=f"pi_{order.public_order_code}",
            actor=self.customer,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        return order

    def test_parallel_queue_transitions_do_not_oversubscribe_inventory(self):
        order_one = self._create_paid_order()
        order_two = self._create_paid_order()

        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def queue_order(order_id):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                local_order = Order.objects.get(pk=order_id)
                transition_order_status(
                    local_order,
                    Order.Status.QUEUED,
                    actor=self.customer,
                )
                with lock:
                    outcomes.append("queued")
            except InventoryServiceError:
                with lock:
                    outcomes.append("insufficient")
            finally:
                close_old_connections()
                connections.close_all()

        thread_one = threading.Thread(target=queue_order, args=(order_one.pk,))
        thread_two = threading.Thread(target=queue_order, args=(order_two.pk,))
        thread_one.start()
        thread_two.start()
        thread_one.join()
        thread_two.join()

        order_one.refresh_from_db()
        order_two.refresh_from_db()
        balance = get_store_balance(self.store, self.inventory_item)

        self.assertCountEqual(outcomes, ["queued", "insufficient"])
        self.assertEqual(balance.on_hand_quantity, Decimal("0.00"))
        self.assertCountEqual(
            [order_one.status, order_two.status],
            [Order.Status.QUEUED, Order.Status.PAID],
        )
