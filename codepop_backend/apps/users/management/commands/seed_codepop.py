from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backward-compatible alias for bootstrap_demo_data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--skip-imports", action="store_true")
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        kwargs = {
            "reset": options["reset"],
            "skip_imports": options["skip_imports"],
        }
        if options["password"]:
            kwargs["password"] = options["password"]
        call_command("bootstrap_demo_data", **kwargs)
