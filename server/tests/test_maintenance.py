from datetime import date
from decimal import Decimal

from apps.maintenance.models import Machine, MachineStatusEvent, MaintenancePolicy
from apps.maintenance.services import (
    MaintenanceServiceError,
    append_machine_status_event,
    create_repair_assignment,
    evaluate_warning_escalation,
)
from django.test import TestCase

from .helpers import (
    assign_store,
    make_machine,
    make_machine_type,
    make_region,
    make_store,
    make_user,
)


class MaintenancePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.machine_type = make_machine_type(
            code="MIXER_A", warning_max_operational_days=2
        )
        cls.machine = make_machine(
            store=cls.store,
            machine_type=cls.machine_type,
            operational_from_date=date(2025, 7, 1),
        )
        cls.repair_staff = make_user(
            email="repair@test.local",
            role="repair_staff",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="manager@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.repair_staff, cls.store)
        MaintenancePolicy.objects.create(
            machine_type=cls.machine_type,
            region=cls.region,
            max_days_between_service=30,
            warning_shutdown_days=2,
            schedule_service_window_days=7,
        )

    def test_warning_status_escalates_to_out_of_order_after_policy_window(self):
        append_machine_status_event(
            self.machine,
            status=Machine.Status.WARNING,
            status_date=date(2026, 3, 1),
            actor=self.repair_staff,
        )
        escalation = evaluate_warning_escalation(
            self.machine,
            as_of_date=date(2026, 3, 4),
            actor=self.repair_staff,
        )

        self.machine.refresh_from_db()
        self.assertIsNotNone(escalation)
        self.assertEqual(self.machine.current_status, Machine.Status.OUT_OF_ORDER)
        self.assertTrue(
            MachineStatusEvent.objects.filter(
                machine=self.machine, status=Machine.Status.OUT_OF_ORDER
            ).exists()
        )

    def test_repair_assignments_only_allow_repair_staff_targets(self):
        with self.assertRaises(MaintenanceServiceError):
            create_repair_assignment(
                self.machine,
                assigned_to=self.manager,
                priority_score=Decimal("10.00"),
            )

        assignment = create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("20.00"),
        )
        self.assertEqual(assignment.assigned_to, self.repair_staff)
