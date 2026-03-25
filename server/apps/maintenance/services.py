from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance
from apps.users.models import User
from apps.users.permissions import user_can_manage_store, user_has_store_scope
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from .models import Machine, MachineStatusEvent, MaintenancePolicy, RepairAssignment

ACTIONABLE_MACHINE_STATUSES = {
    Machine.Status.SCHEDULE_SERVICE,
    Machine.Status.WARNING,
    Machine.Status.ERROR,
    Machine.Status.OUT_OF_ORDER,
}

PRIORITY_BASE_SCORES = {
    Machine.Status.NORMAL: Decimal("0.00"),
    Machine.Status.SCHEDULE_SERVICE: Decimal("20.00"),
    Machine.Status.WARNING: Decimal("50.00"),
    Machine.Status.ERROR: Decimal("80.00"),
    Machine.Status.OUT_OF_ORDER: Decimal("100.00"),
}

REPAIR_ASSIGNMENT_TRANSITIONS = {
    RepairAssignment.Status.SCHEDULED: {
        RepairAssignment.Status.ACKNOWLEDGED,
        RepairAssignment.Status.IN_PROGRESS,
        RepairAssignment.Status.CANCELED,
    },
    RepairAssignment.Status.ACKNOWLEDGED: {
        RepairAssignment.Status.IN_PROGRESS,
        RepairAssignment.Status.BLOCKED,
        RepairAssignment.Status.CANCELED,
    },
    RepairAssignment.Status.IN_PROGRESS: {
        RepairAssignment.Status.BLOCKED,
        RepairAssignment.Status.COMPLETED,
        RepairAssignment.Status.CANCELED,
    },
    RepairAssignment.Status.BLOCKED: {
        RepairAssignment.Status.ACKNOWLEDGED,
        RepairAssignment.Status.IN_PROGRESS,
        RepairAssignment.Status.COMPLETED,
        RepairAssignment.Status.CANCELED,
    },
    RepairAssignment.Status.COMPLETED: {
        RepairAssignment.Status.CLOSED,
    },
}

REPAIR_STATUS_EVENT_TYPES = {
    RepairAssignment.Status.ACKNOWLEDGED: "repair_assignment.acknowledged",
    RepairAssignment.Status.IN_PROGRESS: "repair_assignment.started",
    RepairAssignment.Status.BLOCKED: "repair_assignment.blocked",
    RepairAssignment.Status.COMPLETED: "repair_assignment.completed",
    RepairAssignment.Status.CLOSED: "repair_assignment.closed",
    RepairAssignment.Status.CANCELED: "repair_assignment.canceled",
}


class MaintenanceServiceError(Exception):
    pass


class RepairAssignmentStateError(MaintenanceServiceError):
    pass


def resolve_effective_policy(machine):
    policy = (
        MaintenancePolicy.objects.filter(
            machine_type=machine.machine_type,
            region=machine.store.region,
            is_active=True,
        )
        .order_by("-region_id")
        .first()
    )
    if policy:
        return {
            "max_days_between_service": policy.max_days_between_service,
            "warning_shutdown_days": policy.warning_shutdown_days,
            "schedule_service_window_days": policy.schedule_service_window_days,
        }
    return {
        "max_days_between_service": machine.machine_type.default_service_interval_days,
        "warning_shutdown_days": machine.machine_type.warning_max_operational_days,
        "schedule_service_window_days": machine.machine_type.default_service_interval_days,
    }


def route_batch_key_for_machine(machine):
    return f"{machine.store.region.code}-{slugify(machine.store.city)}"


def get_active_repair_assignment(machine):
    return (
        machine.repair_assignments.filter(
            status__in=RepairAssignment.actionable_statuses()
        )
        .select_related("assigned_to", "store", "machine")
        .order_by("-priority_score", "scheduled_for", "-created_at")
        .first()
    )


def calculate_machine_priority(machine, *, as_of_date=None):
    as_of_date = as_of_date or timezone.localdate()
    score = PRIORITY_BASE_SCORES.get(machine.current_status, Decimal("0.00"))

    if machine.current_status_date:
        elapsed_days = max((as_of_date - machine.current_status_date).days, 0)
        urgency_multiplier = (
            Decimal("5.00")
            if machine.current_status
            in {Machine.Status.ERROR, Machine.Status.OUT_OF_ORDER}
            else Decimal("3.00")
        )
        score += Decimal(elapsed_days) * urgency_multiplier

    if machine.next_service_due_date and as_of_date > machine.next_service_due_date:
        overdue_days = (as_of_date - machine.next_service_due_date).days
        score += min(Decimal(overdue_days) * Decimal("4.00"), Decimal("25.00"))

    recent_failures = machine.status_events.filter(
        status__in=[
            Machine.Status.WARNING,
            Machine.Status.ERROR,
            Machine.Status.OUT_OF_ORDER,
        ],
        status_date__gte=as_of_date - timedelta(days=30),
    ).count()
    score += min(Decimal(recent_failures) * Decimal("2.00"), Decimal("10.00"))

    if (
        get_active_repair_assignment(machine) is None
        and machine.current_status in ACTIONABLE_MACHINE_STATUSES
    ):
        score += Decimal("5.00")

    return score.quantize(Decimal("0.01"))


def recommended_assignment_time(machine, *, now=None):
    now = now or timezone.now()
    offset_hours = {
        Machine.Status.OUT_OF_ORDER: 1,
        Machine.Status.ERROR: 4,
        Machine.Status.WARNING: 12,
        Machine.Status.SCHEDULE_SERVICE: 36,
    }.get(machine.current_status, 24)
    return now + timedelta(hours=offset_hours)


def select_repair_assignee(machine):
    return (
        User.objects.filter(
            role=User.Role.REPAIR_STAFF,
            status=User.Status.ACTIVE,
            store_assignments__store=machine.store,
        )
        .annotate(
            open_assignment_count=Count(
                "repair_assignments",
                filter=Q(
                    repair_assignments__status__in=RepairAssignment.actionable_statuses()
                ),
            )
        )
        .order_by("open_assignment_count", "last_name", "first_name", "email")
        .first()
    )


def _assignment_scope_payload(assignment):
    return {
        "store_id": str(assignment.store_id),
        "region_code": assignment.store.region.code,
        "assigned_to_id": str(assignment.assigned_to_id),
    }


def _assignment_outbox_payload(assignment, *, note=""):
    return {
        "assignment_id": str(assignment.pk),
        "machine_id": str(assignment.machine_id),
        "assigned_to_id": str(assignment.assigned_to_id),
        "status": assignment.status,
        "priority_score": str(assignment.priority_score),
        "note": note,
        "route_batch_key": assignment.route_batch_key,
        "follow_up_required": assignment.follow_up_required,
    }


def _validate_assignment_actor(assignment, *, actor, allow_store_oversight=False):
    if actor is None:
        return
    if actor.role == actor.Role.SUPER_ADMIN:
        return
    if actor.role == actor.Role.REPAIR_STAFF and actor.pk == assignment.assigned_to_id:
        return
    if allow_store_oversight and user_can_manage_store(actor, assignment.store):
        return
    raise MaintenanceServiceError("You cannot change this repair assignment.")


def _status_change_action(new_status):
    return REPAIR_STATUS_EVENT_TYPES.get(new_status, f"repair_assignment.{new_status}")


def _apply_note(assignment, note):
    clean_note = (note or "").strip()
    if clean_note:
        assignment.notes = clean_note
    return clean_note


@transaction.atomic
def append_machine_status_event(
    machine, *, status, status_date, notes="", source_import_job=None, actor=None
):
    before = serialize_instance(machine)
    event = MachineStatusEvent.objects.create(
        machine=machine,
        status=status,
        status_date=status_date,
        notes=notes,
        source_import_job=source_import_job,
    )
    policy = resolve_effective_policy(machine)
    machine.current_status = status
    machine.current_status_date = status_date
    if status in {Machine.Status.REPAIR_END, Machine.Status.NORMAL}:
        machine.last_service_date = status_date
        machine.next_service_due_date = status_date + timedelta(
            days=policy["max_days_between_service"]
        )
    machine.save()

    if status in ACTIONABLE_MACHINE_STATUSES:
        create_outbox_event(
            event_type=f"machine.{status}",
            instance=machine,
            payload={"status": status, "status_date": status_date.isoformat()},
            source_scope={
                "store_id": str(machine.store_id),
                "region_code": machine.store.region.code,
            },
        )
        ensure_repair_assignment(
            machine,
            actor=actor,
            note=notes
            or f"Machine entered {machine.get_current_status_display().lower()} status.",
        )
    create_audit_log(
        actor=actor,
        action="machine.status_recorded",
        instance=machine,
        before=before,
        after=serialize_instance(machine),
    )
    return event


@transaction.atomic
def create_repair_assignment(
    machine,
    *,
    assigned_to,
    priority_score=None,
    scheduled_for=None,
    created_by_system=True,
    notes="",
    actor=None,
):
    if assigned_to.role != assigned_to.Role.REPAIR_STAFF:
        raise MaintenanceServiceError(
            "Repair assignments may only target repair staff users."
        )
    if not user_has_store_scope(assigned_to, machine.store):
        raise MaintenanceServiceError(
            "Assigned repair staff must already have scope for the machine store."
        )

    assignment = RepairAssignment.objects.create(
        assigned_to=assigned_to,
        machine=machine,
        store=machine.store,
        priority_score=(
            priority_score
            if priority_score is not None
            else calculate_machine_priority(machine)
        ),
        scheduled_for=(
            scheduled_for
            if scheduled_for is not None
            else recommended_assignment_time(machine)
        ),
        created_by_system=created_by_system,
        route_batch_key=route_batch_key_for_machine(machine),
        notes=notes,
    )
    create_outbox_event(
        event_type="repair_assignment.created",
        instance=assignment,
        payload=_assignment_outbox_payload(assignment, note=notes),
        source_scope=_assignment_scope_payload(assignment),
    )
    create_audit_log(
        actor=actor,
        action="repair_assignment.created",
        instance=assignment,
        after=serialize_instance(assignment),
    )
    return assignment


@transaction.atomic
def ensure_repair_assignment(machine, *, actor=None, preferred_assignee=None, note=""):
    if machine.current_status not in ACTIONABLE_MACHINE_STATUSES:
        return None

    priority_score = calculate_machine_priority(machine)
    scheduled_for = recommended_assignment_time(machine)
    route_batch_key = route_batch_key_for_machine(machine)
    assignment = get_active_repair_assignment(machine)
    if assignment is not None:
        before = serialize_instance(assignment)
        changed_fields = []
        if assignment.priority_score != priority_score:
            assignment.priority_score = priority_score
            changed_fields.append("priority_score")
        if assignment.route_batch_key != route_batch_key:
            assignment.route_batch_key = route_batch_key
            changed_fields.append("route_batch_key")
        if assignment.scheduled_for != scheduled_for:
            assignment.scheduled_for = scheduled_for
            changed_fields.append("scheduled_for")
        clean_note = _apply_note(assignment, note)
        if clean_note:
            changed_fields.append("notes")
        if changed_fields:
            assignment.save(update_fields=changed_fields + ["updated_at"])
            create_audit_log(
                actor=actor,
                action="repair_assignment.reprioritized",
                instance=assignment,
                before=before,
                after=serialize_instance(assignment),
            )
        return assignment

    assignee = preferred_assignee
    if assignee is not None and not user_has_store_scope(assignee, machine.store):
        assignee = None
    assignee = assignee or select_repair_assignee(machine)
    if assignee is None:
        return None

    return create_repair_assignment(
        machine,
        assigned_to=assignee,
        priority_score=priority_score,
        scheduled_for=scheduled_for,
        created_by_system=True,
        notes=note,
        actor=actor,
    )


@transaction.atomic
def evaluate_warning_escalation(machine, *, as_of_date, actor=None):
    if (
        machine.current_status != Machine.Status.WARNING
        or not machine.current_status_date
    ):
        return None
    policy = resolve_effective_policy(machine)
    elapsed_days = (as_of_date - machine.current_status_date).days
    if elapsed_days < policy["warning_shutdown_days"]:
        ensure_repair_assignment(machine, actor=actor)
        return None
    return append_machine_status_event(
        machine,
        status=Machine.Status.OUT_OF_ORDER,
        status_date=as_of_date,
        notes="Automatically escalated from warning due to maintenance policy.",
        actor=actor,
    )


@transaction.atomic
def evaluate_error_escalation(machine, *, as_of_date, actor=None):
    if (
        machine.current_status != Machine.Status.ERROR
        or not machine.current_status_date
    ):
        return None
    max_days = machine.machine_type.error_max_days
    if max_days <= 0:
        ensure_repair_assignment(machine, actor=actor)
        return None
    elapsed_days = (as_of_date - machine.current_status_date).days
    if elapsed_days < max_days:
        ensure_repair_assignment(machine, actor=actor)
        return None
    return append_machine_status_event(
        machine,
        status=Machine.Status.OUT_OF_ORDER,
        status_date=as_of_date,
        notes="Automatically escalated from error due to machine-type policy.",
        actor=actor,
    )


@transaction.atomic
def evaluate_service_window(machine, *, as_of_date, actor=None):
    if not machine.next_service_due_date:
        return None
    if machine.current_status in {
        Machine.Status.WARNING,
        Machine.Status.ERROR,
        Machine.Status.OUT_OF_ORDER,
        Machine.Status.REPAIR_START,
    }:
        return None

    policy = resolve_effective_policy(machine)
    window_opens = machine.next_service_due_date - timedelta(
        days=policy["schedule_service_window_days"]
    )
    if as_of_date < window_opens:
        return None
    if machine.current_status == Machine.Status.SCHEDULE_SERVICE:
        return ensure_repair_assignment(
            machine,
            actor=actor,
            note="Preventive service remains inside the configured maintenance window.",
        )

    return append_machine_status_event(
        machine,
        status=Machine.Status.SCHEDULE_SERVICE,
        status_date=as_of_date,
        notes="Machine entered the configured preventive service window.",
        actor=actor,
    )


def run_maintenance_policy_checks(*, machines=None, as_of_date=None, actor=None):
    as_of_date = as_of_date or timezone.localdate()
    machines = machines or Machine.objects.select_related("store", "machine_type")
    summary = {"service_window": 0, "warning_escalation": 0, "error_escalation": 0}
    for machine in machines:
        if evaluate_service_window(machine, as_of_date=as_of_date, actor=actor):
            summary["service_window"] += 1
        if evaluate_warning_escalation(machine, as_of_date=as_of_date, actor=actor):
            summary["warning_escalation"] += 1
        if evaluate_error_escalation(machine, as_of_date=as_of_date, actor=actor):
            summary["error_escalation"] += 1
    return summary


def _transition_assignment(
    assignment, *, new_status, actor=None, note="", follow_up_required=None
):
    before = serialize_instance(assignment)
    allowed = REPAIR_ASSIGNMENT_TRANSITIONS.get(assignment.status, set())
    if new_status not in allowed:
        raise RepairAssignmentStateError(
            f"Cannot transition assignment from {assignment.status} to {new_status}."
        )

    now = timezone.now()
    assignment.status = new_status
    clean_note = _apply_note(assignment, note)

    if (
        new_status == RepairAssignment.Status.ACKNOWLEDGED
        and assignment.acknowledged_at is None
    ):
        assignment.acknowledged_at = now
    if new_status == RepairAssignment.Status.IN_PROGRESS:
        if assignment.acknowledged_at is None:
            assignment.acknowledged_at = now
        if assignment.started_at is None:
            assignment.started_at = now
    if new_status == RepairAssignment.Status.BLOCKED:
        assignment.blocked_at = now
        assignment.blocker_summary = clean_note or assignment.blocker_summary
    if new_status == RepairAssignment.Status.COMPLETED:
        assignment.completed_at = now
        assignment.blocker_summary = ""
    if new_status == RepairAssignment.Status.CLOSED:
        assignment.closed_at = now
        assignment.follow_up_required = False
    if new_status == RepairAssignment.Status.CANCELED:
        assignment.blocker_summary = ""
    if follow_up_required is not None:
        assignment.follow_up_required = follow_up_required

    assignment.save()
    event_type = _status_change_action(new_status)
    create_outbox_event(
        event_type=event_type,
        instance=assignment,
        payload=_assignment_outbox_payload(assignment, note=clean_note),
        source_scope=_assignment_scope_payload(assignment),
    )
    create_audit_log(
        actor=actor,
        action=event_type,
        instance=assignment,
        before=before,
        after=serialize_instance(assignment),
    )
    return assignment


@transaction.atomic
def acknowledge_repair_assignment(assignment, *, actor=None, note=""):
    _validate_assignment_actor(assignment, actor=actor)
    return _transition_assignment(
        assignment,
        new_status=RepairAssignment.Status.ACKNOWLEDGED,
        actor=actor,
        note=note,
    )


@transaction.atomic
def start_repair_assignment(assignment, *, actor=None, note=""):
    _validate_assignment_actor(assignment, actor=actor)
    assignment = _transition_assignment(
        assignment,
        new_status=RepairAssignment.Status.IN_PROGRESS,
        actor=actor,
        note=note or "Repair work started.",
    )
    append_machine_status_event(
        assignment.machine,
        status=Machine.Status.REPAIR_START,
        status_date=timezone.localdate(),
        notes=note or "Repair work started.",
        actor=actor,
    )
    return assignment


@transaction.atomic
def block_repair_assignment(
    assignment, *, actor=None, note="", follow_up_required=True
):
    _validate_assignment_actor(assignment, actor=actor)
    return _transition_assignment(
        assignment,
        new_status=RepairAssignment.Status.BLOCKED,
        actor=actor,
        note=note or "Repair is blocked and needs follow-up.",
        follow_up_required=follow_up_required,
    )


@transaction.atomic
def add_repair_assignment_note(
    assignment, *, actor=None, note="", follow_up_required=None
):
    _validate_assignment_actor(assignment, actor=actor, allow_store_oversight=True)
    clean_note = (note or "").strip()
    if not clean_note:
        raise MaintenanceServiceError("Repair updates require a note.")

    before = serialize_instance(assignment)
    assignment.notes = clean_note
    if follow_up_required is not None:
        assignment.follow_up_required = follow_up_required
    assignment.save()
    create_outbox_event(
        event_type="repair_assignment.updated",
        instance=assignment,
        payload=_assignment_outbox_payload(assignment, note=clean_note),
        source_scope=_assignment_scope_payload(assignment),
    )
    create_audit_log(
        actor=actor,
        action="repair_assignment.updated",
        instance=assignment,
        before=before,
        after=serialize_instance(assignment),
    )
    return assignment


@transaction.atomic
def complete_repair_assignment(assignment, *, actor=None, note=""):
    _validate_assignment_actor(assignment, actor=actor)
    assignment = _transition_assignment(
        assignment,
        new_status=RepairAssignment.Status.COMPLETED,
        actor=actor,
        note=note or "Repair work completed.",
        follow_up_required=False,
    )
    repair_date = timezone.localdate()
    append_machine_status_event(
        assignment.machine,
        status=Machine.Status.REPAIR_END,
        status_date=repair_date,
        notes=note or "Repair work completed.",
        actor=actor,
    )
    append_machine_status_event(
        assignment.machine,
        status=Machine.Status.NORMAL,
        status_date=repair_date,
        notes="Machine returned to normal operation after repair completion.",
        actor=actor,
    )
    return assignment


@transaction.atomic
def close_repair_assignment(assignment, *, actor=None, note=""):
    _validate_assignment_actor(assignment, actor=actor, allow_store_oversight=True)
    return _transition_assignment(
        assignment,
        new_status=RepairAssignment.Status.CLOSED,
        actor=actor,
        note=note or "Assignment closed.",
    )


@transaction.atomic
def claim_machine_for_repair(machine, *, actor):
    if actor.role != actor.Role.REPAIR_STAFF:
        raise MaintenanceServiceError("Only repair staff may claim repair work.")
    if not user_has_store_scope(actor, machine.store):
        raise MaintenanceServiceError(
            "You cannot claim work outside your assigned stores."
        )
    return ensure_repair_assignment(
        machine,
        actor=actor,
        preferred_assignee=actor,
        note="Repair visit claimed from the urgency queue.",
    )


@transaction.atomic
def auto_assign_machine(machine, *, actor=None):
    if actor and actor.role not in {
        actor.Role.MANAGER,
        actor.Role.ADMIN,
        actor.Role.SUPER_ADMIN,
    }:
        raise MaintenanceServiceError(
            "Only managers, admins, or super admins may assign repair work."
        )
    if (
        actor
        and actor.role != actor.Role.SUPER_ADMIN
        and not user_can_manage_store(actor, machine.store)
    ):
        raise MaintenanceServiceError(
            "You cannot assign work outside your store scope."
        )
    return ensure_repair_assignment(
        machine,
        actor=actor,
        note="Repair visit assigned from the maintenance workspace.",
    )
