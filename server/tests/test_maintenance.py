from datetime import date
from decimal import Decimal

from apps.maintenance.models import (
    Machine,
    MachineStatusEvent,
    MaintenancePolicy,
    RepairAssignment,
)
from apps.maintenance.selectors import build_route_groups
from apps.maintenance.services import (
    MaintenanceServiceError,
    acknowledge_repair_assignment,
    add_repair_assignment_note,
    append_machine_status_event,
    block_repair_assignment,
    close_repair_assignment,
    complete_repair_assignment,
    create_repair_assignment,
    evaluate_error_escalation,
    evaluate_service_window,
    evaluate_warning_escalation,
    start_repair_assignment,
)
from apps.notifications.models import Notification
from django.test import TestCase

from .helpers import (
    assign_store,
    make_machine,
    make_machine_type,
    make_region,
    make_store,
    make_user,
)


class MaintenanceWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.store_two = make_store(
            store_code="C002",
            region=cls.region,
            name="Logan South",
            city="Logan",
            address_line_1="456 Center St",
            latitude="41.720000",
            longitude="-111.850000",
        )
        cls.machine_type = make_machine_type(
            code="MIXER_A",
            warning_max_operational_days=2,
            error_max_days=1,
        )
        cls.machine = make_machine(
            store=cls.store,
            machine_type=cls.machine_type,
            operational_from_date=date(2025, 7, 1),
        )
        cls.second_machine = make_machine(
            store=cls.store_two,
            machine_type=cls.machine_type,
            operational_from_date=date(2025, 8, 1),
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
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.repair_staff, cls.store)
        assign_store(cls.repair_staff, cls.store_two)
        assign_store(cls.manager, cls.store)
        assign_store(cls.admin, cls.store)
        MaintenancePolicy.objects.create(
            machine_type=cls.machine_type,
            region=cls.region,
            max_days_between_service=30,
            warning_shutdown_days=2,
            schedule_service_window_days=7,
        )

    def test_warning_status_escalates_and_creates_assignment_notifications(self):
        with self.captureOnCommitCallbacks(execute=True):
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
        assignment = RepairAssignment.objects.get(machine=self.machine)
        self.assertIsNotNone(escalation)
        self.assertEqual(self.machine.current_status, Machine.Status.OUT_OF_ORDER)
        self.assertEqual(assignment.assigned_to, self.repair_staff)
        self.assertEqual(assignment.route_batch_key, "C-logan")
        self.assertTrue(
            MachineStatusEvent.objects.filter(
                machine=self.machine,
                status=Machine.Status.OUT_OF_ORDER,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.repair_staff,
                title="Repair assignment created",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager,
                title="Machine out of order",
            ).exists()
        )

    def test_error_escalation_uses_machine_type_policy(self):
        append_machine_status_event(
            self.machine,
            status=Machine.Status.ERROR,
            status_date=date(2026, 3, 10),
            actor=self.repair_staff,
        )
        escalation = evaluate_error_escalation(
            self.machine,
            as_of_date=date(2026, 3, 11),
            actor=self.repair_staff,
        )

        self.machine.refresh_from_db()
        self.assertIsNotNone(escalation)
        self.assertEqual(self.machine.current_status, Machine.Status.OUT_OF_ORDER)

    def test_service_window_creates_schedule_service_assignment(self):
        self.machine.next_service_due_date = date(2026, 3, 30)
        self.machine.save(update_fields=["next_service_due_date"])

        evaluate_service_window(
            self.machine,
            as_of_date=date(2026, 3, 24),
            actor=self.repair_staff,
        )

        self.machine.refresh_from_db()
        assignment = RepairAssignment.objects.get(machine=self.machine)
        self.assertEqual(self.machine.current_status, Machine.Status.SCHEDULE_SERVICE)
        self.assertEqual(assignment.status, RepairAssignment.Status.SCHEDULED)

    def test_assignment_lifecycle_updates_machine_history_and_terminal_states(self):
        assignment = create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("20.00"),
        )

        with self.captureOnCommitCallbacks(execute=True):
            acknowledge_repair_assignment(
                assignment,
                actor=self.repair_staff,
                note="Acknowledged on mobile.",
            )
            start_repair_assignment(
                assignment,
                actor=self.repair_staff,
                note="Starting diagnostics.",
            )
            block_repair_assignment(
                assignment,
                actor=self.repair_staff,
                note="Waiting on a gasket.",
            )
            add_repair_assignment_note(
                assignment,
                actor=self.repair_staff,
                note="Parts confirmed for tomorrow morning.",
                follow_up_required=True,
            )
            start_repair_assignment(
                assignment,
                actor=self.repair_staff,
                note="Returning to the repair after parts arrival.",
            )
            complete_repair_assignment(
                assignment,
                actor=self.repair_staff,
                note="Machine repaired and tested.",
            )
            close_repair_assignment(
                assignment,
                actor=self.manager,
                note="Manager verified normal operation.",
            )

        assignment.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(assignment.status, RepairAssignment.Status.CLOSED)
        self.assertTrue(assignment.acknowledged_at)
        self.assertTrue(assignment.started_at)
        self.assertTrue(assignment.blocked_at)
        self.assertTrue(assignment.completed_at)
        self.assertTrue(assignment.closed_at)
        self.assertEqual(self.machine.current_status, Machine.Status.NORMAL)
        self.assertTrue(
            MachineStatusEvent.objects.filter(
                machine=self.machine,
                status=Machine.Status.REPAIR_START,
            ).exists()
        )
        self.assertTrue(
            MachineStatusEvent.objects.filter(
                machine=self.machine,
                status=Machine.Status.REPAIR_END,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager,
                title="Repair visit blocked",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager,
                title="Repair visit completed",
            ).exists()
        )

    def test_route_groups_cluster_assignments_by_city_batch(self):
        assignment_one = create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("40.00"),
        )
        assignment_two = create_repair_assignment(
            self.second_machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("30.00"),
        )

        route_groups = build_route_groups([assignment_one, assignment_two])

        self.assertEqual(len(route_groups), 1)
        self.assertEqual(route_groups[0]["assignment_count"], 2)
        self.assertEqual(route_groups[0]["store_count"], 2)
        self.assertEqual(route_groups[0]["label"], "Logan, UT")

    def test_repair_assignments_only_allow_repair_staff_targets(self):
        with self.assertRaises(MaintenanceServiceError):
            create_repair_assignment(
                self.machine,
                assigned_to=self.manager,
                priority_score=Decimal("10.00"),
            )
