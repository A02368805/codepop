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
from django.urls import reverse

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


class MaintenanceWorkspaceViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.other_store = make_store(
            store_code="C002",
            region=cls.region,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.machine_type = make_machine_type(code="MIXER_B")
        cls.machine = make_machine(
            store=cls.store,
            machine_type=cls.machine_type,
            operational_from_date=date(2025, 7, 1),
        )
        append_machine_status_event(
            cls.machine,
            status=Machine.Status.ERROR,
            status_date=date(2026, 3, 20),
        )

        cls.repair_staff = make_user(
            email="repair-workspace@test.local",
            role="repair_staff",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="manager-workspace@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.out_of_scope_manager = make_user(
            email="manager-out-of-scope@test.local",
            role="manager",
            preferred_store=cls.other_store,
            default_region=cls.region,
        )
        assign_store(cls.repair_staff, cls.store)
        assign_store(cls.manager, cls.store)
        assign_store(cls.out_of_scope_manager, cls.other_store)

    def test_machine_assign_endpoint_creates_assignment_for_scoped_user(self):
        self.client.force_login(self.repair_staff)
        response = self.client.post(
            reverse("maintenance:machine-assign", args=[self.machine.pk]),
            {"status": "error"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Repair Assignments")
        self.assertTrue(
            self.machine.repair_assignments.filter(
                assigned_to=self.repair_staff
            ).exists()
        )

    def test_assignment_action_endpoint_advances_status_for_assignee(self):
        assignment = create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("85.00"),
            notes="Seeded for lifecycle test.",
        )
        self.client.force_login(self.repair_staff)

        ack_response = self.client.post(
            reverse("maintenance:assignment-action", args=[assignment.pk]),
            {"action": "acknowledge", "note": "Acknowledged on route."},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(ack_response.status_code, 200)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, assignment.Status.ACKNOWLEDGED)

        start_response = self.client.post(
            reverse("maintenance:assignment-action", args=[assignment.pk]),
            {"action": "start", "note": "On site now."},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(start_response.status_code, 200)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, assignment.Status.IN_PROGRESS)

    def test_assignment_action_endpoint_blocks_out_of_scope_actor(self):
        assignment = create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("90.00"),
        )
        self.client.force_login(self.out_of_scope_manager)
        response = self.client.post(
            reverse("maintenance:assignment-action", args=[assignment.pk]),
            {"action": "acknowledge"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 403)

    def test_workspace_renders_stacked_assignments_panel_with_view_all_toggle(self):
        create_repair_assignment(
            self.machine,
            assigned_to=self.repair_staff,
            priority_score=Decimal("70.00"),
            notes="Seeded preview assignment.",
        )
        self.client.force_login(self.repair_staff)

        response = self.client.get(reverse("maintenance:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Route-Aware Queue")
        self.assertContains(response, "Repair Assignments")
        self.assertContains(response, "View all")

        html = response.content.decode()
        self.assertLess(html.find("Route-Aware Queue"), html.find("Repair Assignments"))

        expanded_response = self.client.get(
            reverse("maintenance:index"),
            {"assignments": "all"},
        )
        self.assertEqual(expanded_response.status_code, 200)
        self.assertContains(expanded_response, "Show preview")
