from decimal import Decimal
from unittest.mock import patch

from apps.orders.models import Order
from apps.orders.services import create_order
from apps.payments.models import (
    PaymentTransaction,
    PaymentWebhookEvent,
    RevenueLedgerEntry,
)
from apps.payments.services import record_payment_pending, record_payment_success
from django.test import TestCase
from django.urls import reverse

from .helpers import make_inventory_item, make_region, make_store, make_user


class PaymentWebhookSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="webhook@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        make_inventory_item(sku="SYRUP-STRAWBERRY")

    def _create_paid_order(self):
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.50"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.50",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=self.customer,
        )
        record_payment_pending(order, payment_intent_id="pi_webhook_1")
        record_payment_success(order, payment_intent_id="pi_webhook_1", actor=self.customer)
        return order

    @patch("apps.payments.views.construct_webhook_event")
    @patch("apps.payments.views.finalize_stripe_checkout")
    def test_checkout_completed_webhook_returns_200_when_replayed_or_invalid_state(
        self,
        mock_finalize,
        mock_construct,
    ):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_1", "metadata": {"order_code": "FS-C-C001-TEST"}}},
        }
        mock_finalize.side_effect = RuntimeError("already processed")

        response = self.client.post(
            reverse("payments:stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

        self.assertEqual(response.status_code, 200)

    @patch("apps.payments.views.construct_webhook_event")
    @patch("apps.payments.views.finalize_stripe_checkout")
    def test_checkout_completed_webhook_is_processed_once_per_event_id(
        self,
        mock_finalize,
        mock_construct,
    ):
        mock_construct.return_value = {
            "id": "evt_once_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_once",
                    "metadata": {"order_code": "FS-C-C001-ONCE"},
                }
            },
        }

        first = self.client.post(
            reverse("payments:stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )
        second = self.client.post(
            reverse("payments:stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(mock_finalize.call_count, 1)
        self.assertEqual(
            PaymentWebhookEvent.objects.filter(provider_event_id="evt_once_1").count(),
            1,
        )

    @patch("apps.payments.views.construct_webhook_event")
    def test_refund_webhook_is_ignored_when_payment_already_refunded(self, mock_construct):
        order = self._create_paid_order()
        order.status = Order.Status.REFUNDED
        order.save(update_fields=["status", "updated_at"])

        payment = order.payment_transaction
        payment.status = PaymentTransaction.Status.REFUNDED
        payment.amount_refunded = payment.amount_captured
        payment.stripe_payment_intent_id = "pi_refund_done"
        payment.save(
            update_fields=[
                "status",
                "amount_refunded",
                "stripe_payment_intent_id",
                "updated_at",
            ]
        )

        existing_refund_entries = RevenueLedgerEntry.objects.filter(
            order=order,
            entry_type=RevenueLedgerEntry.EntryType.REFUND,
        ).count()

        mock_construct.return_value = {
            "type": "charge.refunded",
            "data": {"object": {"payment_intent": "pi_refund_done"}},
        }

        response = self.client.post(
            reverse("payments:stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(
                order=order,
                entry_type=RevenueLedgerEntry.EntryType.REFUND,
            ).count(),
            existing_refund_entries,
        )
