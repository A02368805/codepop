from datetime import timedelta
from decimal import Decimal

from apps.inventory.services import get_store_balance
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.orders.pickup import pickup_time_choices
from apps.orders.services import create_order, transition_order_status
from apps.payments.models import PaymentTransaction
from apps.payments.services import record_payment_pending, record_payment_success
from apps.sync.models import AuditLog, SyncOutboxEvent
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


def seed_menu_inventory(store):
    inventory_rows = [
        ("BASE-LEMON-LIME", "Lemon Lime Base", "soda", "5.00"),
        ("SYRUP-STRAWBERRY", "Strawberry Syrup", "syrup", "5.00"),
        ("CUPS-24OZ", "24oz Cups", "cups", "50.00"),
        ("LIDS-24OZ", "24oz Lids", "lids", "50.00"),
    ]
    for sku, name, category, threshold in inventory_rows:
        item = make_inventory_item(
            sku=sku, name=name, category=category, threshold=threshold
        )
        balance = get_store_balance(store, item)
        balance.on_hand_quantity = Decimal("250.00")
        balance.reorder_threshold = Decimal(threshold)
        balance.save()


class PromptFourIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="integration.customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="integration.manager@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.logistics = make_user(
            email="integration.logistics@test.local",
            role="logistics_manager",
            default_region=cls.region,
        )
        assign_store(cls.manager, cls.store)
        assign_region(cls.logistics, cls.region)
        seed_menu_inventory(cls.store)

    def _future_pickup_value(self):
        return pickup_time_choices(now=timezone.now())[1][0]

    def test_mock_checkout_creates_mock_transaction_and_recommendation_notification(
        self,
    ):
        self.client.force_login(self.customer)
        self.client.post(
            reverse("orders:customize", args=[self.store.store_code, "berry-burst"]),
            {
                "size": "medium",
                "soda": "lemon-lime",
                "syrups": ["strawberry"],
                "add_ins": [],
                "quantity": 1,
                "notes": "integration test",
            },
            follow=True,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("orders:checkout"),
                {"pickup_time_choice": self._future_pickup_value()},
                follow=True,
            )

        from apps.analytics.tasks import refresh_account_recommendations
        from apps.sync.services import process_pending_outbox_events

        order = Order.objects.get(customer=self.customer)
        payment = order.payment_transaction
        self.assertEqual(order.status, Order.Status.QUEUED)
        self.assertEqual(payment.provider, PaymentTransaction.Provider.MOCK)
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertContains(
            response, "Demo payment mode completed the order instantly."
        )

        # Process pending sync events to dispatch notifications
        process_pending_outbox_events(limit=25)
        # Manually trigger recommendation task (should have been triggered by transaction.on_commit)
        refresh_account_recommendations(str(self.customer.pk), reason="Based on your latest order")

        self.assertTrue(
            Notification.objects.filter(
                user=self.customer,
                title="Fresh drink ideas",
            ).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action="payment.succeeded").exists())

    def test_checkout_cancel_marks_pending_payment_failed_for_guest_order(self):
        order = create_order(
            store=self.store,
            customer=None,
            guest_contact={
                "display_name": "Guest Cancel",
                "email": "guest-cancel@test.local",
            },
            pickup_time_requested=timezone.now() + timedelta(hours=3),
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [],
                    },
                }
            ],
        )
        record_payment_pending(order, payment_intent_id="pi_cancel_checkout")

        response = self.client.get(
            reverse("payments:checkout-cancel")
            + f"?order_code={order.public_order_code}",
            follow=True,
        )

        order.refresh_from_db()
        payment = order.payment_transaction
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, Order.Status.CANCELED)
        self.assertEqual(payment.status, PaymentTransaction.Status.FAILED)
        self.assertIn("Stripe checkout was canceled", payment.failure_reason)
        self.assertContains(response, "Checkout was canceled.")

    def test_order_ready_dispatches_customer_notification_and_sync_audit(self):
        from apps.sync.services import process_pending_outbox_events

        order = create_order(
            store=self.store,
            customer=self.customer,
            pickup_time_requested=timezone.now() + timedelta(hours=2),
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [
                            {"sku": "BASE-LEMON-LIME", "quantity": "0.50"},
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "0.50"},
                            {"sku": "CUPS-24OZ", "quantity": "1.00"},
                            {"sku": "LIDS-24OZ", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )
        with self.captureOnCommitCallbacks(execute=True):
            record_payment_pending(order, payment_intent_id="pi_ready_notification")
            record_payment_success(
                order, payment_intent_id="pi_ready_notification", actor=self.customer
            )
            transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
            transition_order_status(order, Order.Status.PREPARING, actor=self.manager)
            transition_order_status(order, Order.Status.READY, actor=self.manager)

        # Process pending sync events to dispatch notifications
        process_pending_outbox_events(limit=25)

        self.assertTrue(
            SyncOutboxEvent.objects.filter(
                aggregate_id=str(order.pk),
                event_type="order.ready",
                status=SyncOutboxEvent.Status.DISPATCHED,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer,
                title="Your order is ready",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="sync.outbox_processed").exists()
        )
        order.refresh_from_db()
        self.assertTrue(order.locker_number.startswith("L"))
        self.assertRegex(order.locker_code, r"^\d{2}-\d{3}$")

    def test_sync_workspace_is_region_scoped_and_notification_mark_read_requires_login(
        self,
    ):
        self.client.force_login(self.manager)
        manager_response = self.client.get(reverse("sync:index"))
        self.assertEqual(manager_response.status_code, 403)

        self.client.force_login(self.logistics)
        logistics_response = self.client.get(reverse("sync:index"))
        self.assertEqual(logistics_response.status_code, 200)
        self.assertContains(logistics_response, "Outbox health")

        notification = Notification.objects.create(
            user=self.customer,
            title="Manual alert",
            message="Check queue",
        )
        logged_out_client = Client()
        redirect_response = logged_out_client.post(
            reverse("notifications:mark-read", args=[notification.pk]),
            follow=False,
        )
        self.assertEqual(redirect_response.status_code, 302)

        self.client.force_login(self.customer)
        read_response = self.client.post(
            reverse("notifications:mark-read", args=[notification.pk]),
            HTTP_HX_REQUEST="true",
        )
        notification.refresh_from_db()
        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(notification.is_read)
