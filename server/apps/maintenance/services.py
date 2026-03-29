from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance
from django.db import transaction

from .models import Machine, MachineStatusEvent, MaintenancePolicy, RepairAssignment


class MaintenanceServiceError(Exception):
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

    if status in {
        Machine.Status.WARNING,
        Machine.Status.ERROR,
        Machine.Status.OUT_OF_ORDER,
    }:
        create_outbox_event(
            event_type=f"machine.{status}",
            instance=machine,
            payload={"status": status, "status_date": status_date.isoformat()},
            source_scope={
                "store_id": str(machine.store_id),
                "region_code": machine.store.region.code,
            },
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
def evaluate_warning_escalation(machine, *, as_of_date, actor=None):
    if (
        machine.current_status != Machine.Status.WARNING
        or not machine.current_status_date
    ):
        return None
    policy = resolve_effective_policy(machine)
    elapsed_days = (as_of_date - machine.current_status_date).days
    if elapsed_days < policy["warning_shutdown_days"]:
        return None
    return append_machine_status_event(
        machine,
        status=Machine.Status.OUT_OF_ORDER,
        status_date=as_of_date,
        notes="Automatically escalated from warning due to maintenance policy.",
        actor=actor,
    )


@transaction.atomic
def create_repair_assignment(
    machine,
    *,
    assigned_to,
    priority_score=Decimal("0.00"),
    scheduled_for=None,
    created_by_system=True,
    notes="",
):
    if assigned_to.role != assigned_to.Role.REPAIR_STAFF:
        raise MaintenanceServiceError(
            "Repair assignments may only target repair staff users."
        )
    assignment = RepairAssignment.objects.create(
        assigned_to=assigned_to,
        machine=machine,
        store=machine.store,
        priority_score=priority_score,
        scheduled_for=scheduled_for,
        created_by_system=created_by_system,
        notes=notes,
        blocker_summary="",
    )
    create_audit_log(
        actor=assigned_to if not created_by_system else None,
        action="repair_assignment.created",
        instance=assignment,
        after=serialize_instance(assignment),
    )
    return assignment
