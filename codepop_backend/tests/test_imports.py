from datetime import date

from django.test import TestCase

from apps.imports.models import ImportJob
from apps.imports.services import CSVImportError, import_repair_status_csv, import_supply_usage_csv
from apps.inventory.models import SupplySchedule, SupplyUsageRecord
from apps.maintenance.models import Machine, MachineStatusEvent
from apps.notifications.models import Notification
from apps.sync.models import AuditLog

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_machine_type,
    make_region,
    make_store,
    make_user,
)


class CSVImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region_c = make_region(code="C", name="Logan, UT")
        cls.region_g = make_region(
            code="G",
            name="Boise, ID",
            hub_city="Boise",
            hub_state_code="ID",
            latitude="43.615021",
            longitude="-116.202316",
        )
        cls.store_c1 = make_store(store_code="C001", region=cls.region_c, name="Logan Main")
        cls.store_c2 = make_store(
            store_code="C002",
            region=cls.region_c,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.store_g1 = make_store(
            store_code="G001",
            region=cls.region_g,
            name="Boise Capitol",
            city="Boise",
            state_code="ID",
            address_line_1="50 Idaho St",
            postal_code="83702",
            latitude="43.615018",
            longitude="-116.202313",
        )

        cls.logistics = make_user(
            email="logistics@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.repair = make_user(
            email="repair@test.local",
            role="repair_staff",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        assign_region(cls.logistics, cls.region_c)
        assign_store(cls.repair, cls.store_c1)

        cls.inventory_item = make_inventory_item(sku="SYRUP-STRAWBERRY")
        cls.machine_type = make_machine_type(code="MIXER_A")

    def test_supply_usage_import_is_transactional_and_creates_draft_schedule(self):
        csv_text = "\n".join(
            [
                "store_code,inventory_sku,usage_date,quantity_used",
                "C001,SYRUP-STRAWBERRY,2026-03-18,4.50",
                "C002,SYRUP-STRAWBERRY,2026-03-18,2.00",
            ]
        )
        job = import_supply_usage_csv(
            csv_text,
            uploaded_by=self.logistics,
            original_filename="usage.csv",
        )

        self.assertEqual(job.status, ImportJob.Status.SUCCEEDED)
        self.assertEqual(SupplyUsageRecord.objects.count(), 2)
        self.assertEqual(SupplySchedule.objects.filter(created_by_ai=True).count(), 2)
        self.assertTrue(
            Notification.objects.filter(
                user=self.logistics,
                title="Import completed",
            ).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action="import.completed").exists())
        self.assertTrue(
            SupplySchedule.objects.filter(
                store=self.store_c1,
                inventory_item=self.inventory_item,
                status=SupplySchedule.Status.DRAFT,
            ).exists()
        )

    def test_supply_usage_validation_prevents_partial_writes(self):
        csv_text = "\n".join(
            [
                "store_code,inventory_sku,usage_date,quantity_used",
                "C001,SYRUP-STRAWBERRY,2026-03-18,4.50",
                "G001,SYRUP-STRAWBERRY,2026-03-18,3.00",
            ]
        )
        with self.assertRaises(CSVImportError):
            import_supply_usage_csv(
                csv_text,
                uploaded_by=self.logistics,
                original_filename="bad-usage.csv",
            )

        self.assertEqual(SupplyUsageRecord.objects.count(), 0)
        failed_job = ImportJob.objects.get(original_filename="bad-usage.csv")
        self.assertEqual(failed_job.status, ImportJob.Status.FAILED)
        self.assertGreater(failed_job.error_count, 0)
        self.assertTrue(
            Notification.objects.filter(
                user=self.logistics,
                title="Import failed",
            ).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action="import.failed").exists())

    def test_repair_import_validates_store_scope_and_machine_status(self):
        invalid_csv = "\n".join(
            [
                "store_address,machine_type_code,machine_operational_from_date,machine_status,status_date",
                "50 Idaho St Boise ID,MIXER_A,2025-07-01,warning,2026-03-18",
            ]
        )
        with self.assertRaises(CSVImportError):
            import_repair_status_csv(
                invalid_csv,
                uploaded_by=self.repair,
                original_filename="invalid-repair.csv",
            )

        valid_csv = "\n".join(
            [
                "store_address,machine_type_code,machine_operational_from_date,machine_status,status_date",
                "123 Main St Logan UT,MIXER_A,2025-07-01,warning,2026-03-18",
            ]
        )
        job = import_repair_status_csv(
            valid_csv,
            uploaded_by=self.repair,
            original_filename="repair.csv",
        )

        machine = Machine.objects.get(store=self.store_c1, machine_type=self.machine_type)
        self.assertEqual(job.status, ImportJob.Status.SUCCEEDED)
        self.assertEqual(machine.current_status, Machine.Status.WARNING)
        self.assertTrue(MachineStatusEvent.objects.filter(machine=machine, status=Machine.Status.WARNING).exists())
        self.assertTrue(
            Notification.objects.filter(
                user=self.repair,
                title="Import completed",
            ).exists()
        )
