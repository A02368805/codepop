from pathlib import Path

from django.test import SimpleTestCase


class ArchitectureGuardrailTests(SimpleTestCase):
    def test_root_urlconf_uses_canonical_apps_only(self):
        urlconf_path = Path(__file__).resolve().parents[1] / "config" / "urls.py"
        urlconf_source = urlconf_path.read_text(encoding="utf-8")

        self.assertNotIn("include(\"codepop_backend", urlconf_source)
        self.assertNotIn("include('codepop_backend", urlconf_source)
        self.assertNotIn("codepop_backend.urls", urlconf_source)

    def test_canonical_apps_do_not_import_legacy_backend(self):
        apps_root = Path(__file__).resolve().parents[1] / "apps"
        python_files = [
            file_path
            for file_path in apps_root.rglob("*.py")
            if "migrations" not in file_path.parts
        ]

        legacy_import_matches = []
        for file_path in python_files:
            source = file_path.read_text(encoding="utf-8")
            if "import codepop_backend" in source or "from codepop_backend" in source:
                legacy_import_matches.append(str(file_path))

        self.assertEqual(
            legacy_import_matches,
            [],
            msg=(
                "Canonical app modules must not import the frozen legacy backend. "
                f"Found matches in: {legacy_import_matches}"
            ),
        )
