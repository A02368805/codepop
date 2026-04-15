from decimal import Decimal
from unittest.mock import patch

from apps.orders.services import create_order
from apps.payments.services import PaymentGatewayError
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import make_region, make_store, make_user


class PaymentIntentConfirmViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="payment-confirm-customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.other_customer = make_user(
            email="payment-confirm-other@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    def _create_order(self):
        return create_order(
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

    @override_settings(PAYMENT_MODE="mock")
    def test_rejects_confirmation_when_stripe_mode_is_disabled(self):
        order = self._create_order()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("payments:payment-confirm"),
            {"order_code": order.public_order_code, "payment_intent_id": "pi_test_123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("error"),
            "Stripe payments are not enabled in this environment.",
        )

    @override_settings(PAYMENT_MODE="stripe", STRIPE_SECRET_KEY="sk_test_123")
    def test_rejects_users_without_order_access(self):
        order = self._create_order()
        self.client.force_login(self.other_customer)

        response = self.client.post(
            reverse("payments:payment-confirm"),
            {"order_code": order.public_order_code, "payment_intent_id": "pi_test_123"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json().get("error"),
            "You don't have access to this order.",
        )

    @override_settings(PAYMENT_MODE="stripe", STRIPE_SECRET_KEY="sk_test_123")
    @patch("apps.payments.views.finalize_stripe_payment_intent")
    def test_finalizes_intent_and_returns_confirmation_redirect(self, mock_finalize):
        order = self._create_order()
        mock_finalize.return_value = order
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("payments:payment-confirm"),
            {"order_code": order.public_order_code, "payment_intent_id": "pi_test_123"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("order_code"), order.public_order_code)
        self.assertEqual(
            payload.get("redirect_url"),
            reverse("orders:confirmation", args=[order.public_order_code]),
        )
        mock_finalize.assert_called_once_with(
            order_code=order.public_order_code,
            payment_intent_id="pi_test_123",
            actor=self.customer,
        )

    @override_settings(PAYMENT_MODE="stripe", STRIPE_SECRET_KEY="sk_test_123")
    @patch(
        "apps.payments.views.finalize_stripe_payment_intent",
        side_effect=PaymentGatewayError("Payment could not be finalized."),
    )
    def test_returns_400_when_finalize_fails(self, _mock_finalize):
        order = self._create_order()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("payments:payment-confirm"),
            {"order_code": order.public_order_code, "payment_intent_id": "pi_test_123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("error"),
            "Payment could not be finalized.",
        )
