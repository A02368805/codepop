from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Validate Stripe and AI provider integration readiness before go-live."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-warnings",
            action="store_true",
            help="Return success even when warnings are present.",
        )

    def handle(self, *args, **options):
        errors = []
        warnings = []

        payment_mode = str(getattr(settings, "PAYMENT_MODE", "mock") or "mock").lower()
        checkout_flow = str(
            getattr(settings, "PAYMENT_CHECKOUT_FLOW", "hosted") or "hosted"
        ).lower()
        ai_provider = str(
            getattr(settings, "AI_RECOMMENDATION_PROVIDER", "deterministic")
            or "deterministic"
        ).lower()

        if payment_mode not in {"mock", "stripe"}:
            errors.append("PAYMENT_MODE must be 'mock' or 'stripe'.")

        if checkout_flow not in {"hosted", "elements"}:
            errors.append("PAYMENT_CHECKOUT_FLOW must be 'hosted' or 'elements'.")

        if payment_mode == "stripe":
            if not getattr(settings, "STRIPE_SECRET_KEY", ""):
                errors.append("Missing STRIPE_SECRET_KEY for PAYMENT_MODE=stripe.")
            if not getattr(settings, "STRIPE_WEBHOOK_SECRET", ""):
                errors.append("Missing STRIPE_WEBHOOK_SECRET for PAYMENT_MODE=stripe.")
            if checkout_flow == "elements" and not getattr(
                settings, "STRIPE_PUBLISHABLE_KEY", ""
            ):
                errors.append(
                    "Missing STRIPE_PUBLISHABLE_KEY for PAYMENT_CHECKOUT_FLOW=elements."
                )

        if payment_mode == "mock" and checkout_flow == "elements":
            warnings.append(
                "PAYMENT_CHECKOUT_FLOW=elements is ignored while PAYMENT_MODE=mock."
            )

        if ai_provider == "anthropic":
            if not getattr(settings, "ANTHROPIC_API_KEY", ""):
                errors.append(
                    "Missing ANTHROPIC_API_KEY for AI_RECOMMENDATION_PROVIDER=anthropic."
                )
            if not getattr(settings, "ANTHROPIC_MODEL", ""):
                errors.append(
                    "Missing ANTHROPIC_MODEL for AI_RECOMMENDATION_PROVIDER=anthropic."
                )
            timeout = float(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 8))
            retries = int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2))
            if timeout <= 0:
                errors.append("AI_PROVIDER_TIMEOUT_SECONDS must be greater than 0.")
            if retries < 0:
                errors.append("AI_PROVIDER_MAX_RETRIES must be 0 or higher.")

        if ai_provider == "deterministic":
            warnings.append(
                "AI_RECOMMENDATION_PROVIDER is deterministic; external AI is disabled."
            )

        if ai_provider not in {"deterministic", "mock-external", "anthropic"}:
            warnings.append(
                f"AI_RECOMMENDATION_PROVIDER='{ai_provider}' is unknown and will fallback to deterministic."
            )

        self.stdout.write("\nIntegration readiness report")
        self.stdout.write("-" * 28)
        self.stdout.write(f"PAYMENT_MODE={payment_mode}")
        self.stdout.write(f"PAYMENT_CHECKOUT_FLOW={checkout_flow}")
        self.stdout.write(f"AI_RECOMMENDATION_PROVIDER={ai_provider}")

        if warnings:
            self.stdout.write("\nWarnings:")
            for warning in warnings:
                self.stdout.write(f"- {warning}")

        if errors:
            self.stdout.write("\nErrors:")
            for error in errors:
                self.stdout.write(f"- {error}")
            raise CommandError("Integration readiness check failed.")

        if warnings and not options.get("allow_warnings"):
            raise CommandError(
                "Integration readiness has warnings. Re-run with --allow-warnings to proceed."
            )

        self.stdout.write(self.style.SUCCESS("\nIntegration readiness check passed."))
