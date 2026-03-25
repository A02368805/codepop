from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


class PreliveIntegrationsCheckTests(TestCase):
    @override_settings(
        PAYMENT_MODE="stripe",
        PAYMENT_CHECKOUT_FLOW="elements",
        STRIPE_SECRET_KEY="sk_test_123",
        STRIPE_PUBLISHABLE_KEY="pk_test_123",
        STRIPE_WEBHOOK_SECRET="whsec_123",
        AI_RECOMMENDATION_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="anthropic_test",
        ANTHROPIC_MODEL="claude-3-5-haiku-latest",
        AI_PROVIDER_TIMEOUT_SECONDS=8,
        AI_PROVIDER_MAX_RETRIES=2,
    )
    def test_command_passes_for_stripe_and_anthropic_when_config_complete(self):
        out = StringIO()
        call_command("prelive_integrations_check", stdout=out)
        output = out.getvalue()
        self.assertIn("Integration readiness check passed", output)

    @override_settings(
        PAYMENT_MODE="stripe",
        PAYMENT_CHECKOUT_FLOW="elements",
        STRIPE_SECRET_KEY="",
        STRIPE_PUBLISHABLE_KEY="",
        STRIPE_WEBHOOK_SECRET="",
    )
    def test_command_fails_when_required_stripe_keys_missing(self):
        with self.assertRaises(CommandError):
            call_command("prelive_integrations_check")

    @override_settings(
        PAYMENT_MODE="mock",
        PAYMENT_CHECKOUT_FLOW="elements",
        AI_RECOMMENDATION_PROVIDER="deterministic",
    )
    def test_command_fails_on_warnings_without_allow_warnings(self):
        with self.assertRaises(CommandError):
            call_command("prelive_integrations_check")

    @override_settings(
        PAYMENT_MODE="mock",
        PAYMENT_CHECKOUT_FLOW="elements",
        AI_RECOMMENDATION_PROVIDER="deterministic",
    )
    def test_command_passes_with_allow_warnings_flag(self):
        out = StringIO()
        call_command("prelive_integrations_check", "--allow-warnings", stdout=out)
        output = out.getvalue()
        self.assertIn("Warnings", output)
        self.assertIn("passed", output)
