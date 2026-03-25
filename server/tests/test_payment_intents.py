from decimal import Decimal

from apps.orders.models import Order
from apps.orders.services import create_order
from apps.payments.models import PaymentTransaction
from apps.payments.services import record_payment_pending, record_payment_success
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import make_region, make_store, make_user


class PaymentIntentEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="payment-intent@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    def _create_pricing_validated_order(self):
        return create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.50"),
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

    @override_settings(PAYMENT_MODE="mock")
    def test_payment_intent_endpoint_returns_client_secret_and_marks_pending(self):
        order = self._create_pricing_validated_order()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("payments:payment-intent"),
            {"order_code": order.public_order_code},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider"], PaymentTransaction.Provider.MOCK)
        self.assertTrue(payload["client_secret"].startswith("mock_client_secret_"))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAYMENT_PENDING)
        self.assertEqual(order.payment_transaction.status, PaymentTransaction.Status.PENDING)

    @override_settings(PAYMENT_MODE="mock")
    def test_payment_intent_endpoint_rejects_terminal_order_status(self):
        order = self._create_pricing_validated_order()
        order.status = Order.Status.CANCELED
        order.save(update_fields=["status", "updated_at"])

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("payments:payment-intent"),
            {"order_code": order.public_order_code},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Payment intent can only be created", response.json()["error"])

    @override_settings(PAYMENT_MODE="mock")
    def test_payment_status_endpoint_returns_finalized_redirect_when_order_is_queued(self):
        order = self._create_pricing_validated_order()
        record_payment_pending(order, payment_intent_id="pi_status_1")
        record_payment_success(order, payment_intent_id="pi_status_1", actor=self.customer)
        order.refresh_from_db()

        self.client.force_login(self.customer)
        response = self.client.get(
            reverse("payments:payment-status"),
            {"order_code": order.public_order_code},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["order_status"], Order.Status.PAID)
        self.assertEqual(payload["payment_status"], PaymentTransaction.Status.SUCCEEDED)
        self.assertTrue(payload["finalized"])
        self.assertIn(order.public_order_code, payload["redirect_url"])

    def test_payment_status_endpoint_requires_order_scope(self):
        order = self._create_pricing_validated_order()
        outsider = make_user(
            email="payment-intent-outsider@test.local",
            preferred_store=self.store,
            default_region=self.region,
        )
        self.client.force_login(outsider)

        response = self.client.get(
            reverse("payments:payment-status"),
            {"order_code": order.public_order_code},
        )

        self.assertEqual(response.status_code, 403)
