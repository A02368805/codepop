from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class SecurityHardeningTests(TestCase):
    def test_session_and_csrf_defaults_remain_hardened(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")
        self.assertIn("django.middleware.csrf.CsrfViewMiddleware", settings.MIDDLEWARE)

    @patch("apps.payments.views.construct_webhook_event", side_effect=Exception("bad"))
    def test_invalid_webhook_signature_is_rejected(self, mocked_construct_event):
        response = self.client.post(
            reverse("payments:stripe-webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Invalid Stripe webhook signature.", response.content.decode("utf-8")
        )
        mocked_construct_event.assert_called_once()
