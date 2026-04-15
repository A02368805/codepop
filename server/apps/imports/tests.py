from decimal import Decimal
from io import StringIO

from apps.imports.services import (
    CSVImportError,
    parse_repair_status_csv,
    parse_supply_usage_csv,
)
from apps.inventory.models import InventoryItem
from apps.maintenance.models import Machine, MachineType
from apps.stores.models import Store
from django.test import TestCase
from tests.helpers import make_inventory_item, make_region, make_store, make_user


class CSVSupplyUsageDateFormatTests(TestCase):
    """Tests for Bug 15 Part 2: CSV date parsing fails with M/D/YY format"""

    @classmethod
    def setUpTestData(cls):
        from tests.helpers import assign_region

        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.inventory_item = make_inventory_item(sku="SODA-DIET-COKE")
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_region(cls.admin, cls.region)

    def test_supply_usage_csv_parses_mdy_date_format(self):
        """
        Bug 15 Part 2: CSV date parsing fails with M/D/YY format.

        Common date format M/D/YY (e.g., '5/18/26') should be accepted
        instead of requiring ISO format (YYYY-MM-DD).
        """
        csv_text = """store_code,inventory_sku,usage_date,quantity_used
C001,SODA-DIET-COKE,5/18/26,10.00
C001,SODA-DIET-COKE,5/19/26,15.00"""

        try:
            parsed_rows = parse_supply_usage_csv(csv_text, uploaded_by=self.admin)
        except CSVImportError as e:
            self.fail(f"CSV parsing failed: {e.errors}")

        self.assertEqual(len(parsed_rows), 2)
        self.assertEqual(parsed_rows[0].usage_date.year, 2026)
        self.assertEqual(parsed_rows[0].usage_date.month, 5)
        self.assertEqual(parsed_rows[0].usage_date.day, 18)

    def test_supply_usage_csv_parses_iso_date_format(self):
        """CSV should still accept ISO format dates (YYYY-MM-DD)."""
        csv_text = """store_code,inventory_sku,usage_date,quantity_used
C001,SODA-DIET-COKE,2026-05-18,10.00"""

        parsed_rows = parse_supply_usage_csv(csv_text, uploaded_by=self.admin)

        self.assertEqual(len(parsed_rows), 1)
        self.assertEqual(parsed_rows[0].usage_date.year, 2026)

    def test_supply_usage_csv_parses_slash_date_format(self):
        """CSV should accept YYYY/MM/DD format."""
        csv_text = """store_code,inventory_sku,usage_date,quantity_used
C001,SODA-DIET-COKE,2026/05/18,10.00"""

        parsed_rows = parse_supply_usage_csv(csv_text, uploaded_by=self.admin)

        self.assertEqual(len(parsed_rows), 1)
        self.assertEqual(parsed_rows[0].usage_date.year, 2026)


class CSVRepairStatusDateFormatTests(TestCase):
    """Tests for repair status CSV date parsing with flexible formats"""

    @classmethod
    def setUpTestData(cls):
        from tests.helpers import assign_store

        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.machine_type = MachineType.objects.create(
            code="FREEZER",
            name="Freezer Unit",
            default_service_interval_days=90,
            warning_max_operational_days=180,
        )
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.admin, cls.store)

    def test_repair_status_csv_parses_mdy_date_format(self):
        """
        Bug 15 Part 2: Repair status CSV should parse M/D/YY dates.
        """
        # Build the store address lookup string to match what the code expects
        from apps.imports.services import _build_store_address_lookup

        store_address = _build_store_address_lookup(self.store)
        csv_text = f"""store_address,machine_type_code,machine_operational_from_date,machine_status,status_date
{store_address},FREEZER,5/18/26,normal,5/19/26"""

        try:
            parsed_rows = parse_repair_status_csv(csv_text, uploaded_by=self.admin)
        except CSVImportError as e:
            self.fail(f"CSV parsing failed: {e.errors}")

        self.assertEqual(len(parsed_rows), 1)
        self.assertEqual(parsed_rows[0].operational_from_date.year, 2026)
        self.assertEqual(parsed_rows[0].status_date.month, 5)

    def test_repair_status_csv_parses_iso_date_format(self):
        """Repair status CSV should still accept ISO format dates."""
        from apps.imports.services import _build_store_address_lookup

        store_address = _build_store_address_lookup(self.store)
        csv_text = f"""store_address,machine_type_code,machine_operational_from_date,machine_status,status_date
{store_address},FREEZER,2026-05-18,normal,2026-05-19"""

        try:
            parsed_rows = parse_repair_status_csv(csv_text, uploaded_by=self.admin)
        except CSVImportError as e:
            self.fail(f"CSV parsing failed: {e.errors}")

        self.assertEqual(len(parsed_rows), 1)


class CSVHeaderParsingTests(TestCase):
    """Tests for Bug 15 Part 3: CSV header parsing with various formats"""

    @classmethod
    def setUpTestData(cls):
        from tests.helpers import assign_region

        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.inventory_item = make_inventory_item(sku="SODA-DIET-COKE")
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_region(cls.admin, cls.region)

    def test_supply_usage_csv_with_trailing_whitespace_in_headers(self):
        """
        CSV headers with trailing/leading whitespace should be normalized.
        Some CSV generators add spaces after field names.
        """
        csv_text = """store_code ,inventory_sku, usage_date ,quantity_used
C001,SODA-DIET-COKE,2026-05-18,10.00"""

        parsed_rows = parse_supply_usage_csv(csv_text, uploaded_by=self.admin)
        self.assertEqual(len(parsed_rows), 1)
