from __future__ import annotations

from collections import defaultdict

from apps.analytics.recommendations import explain_maintenance_priority
from apps.stores.selectors import stores_visible_to_user
from apps.sync.models import AuditLog
from apps.users.models import User
from django.utils import timezone

from .models import Machine, RepairAssignment
from .services import calculate_machine_priority, route_batch_key_for_machine

AUDIT_LABELS = {
    "repair_assignment.created": "Created",
    "repair_assignment.reprioritized": "Reprioritized",
    "repair_assignment.acknowledged": "Acknowledged",
    "repair_assignment.started": "Started",
    "repair_assignment.blocked": "Blocked",
    "repair_assignment.updated": "Updated",
    "repair_assignment.completed": "Completed",
    "repair_assignment.closed": "Closed",
    "repair_assignment.canceled": "Canceled",
}


def _assignment_scope_queryset(user):
    queryset = RepairAssignment.objects.select_related(
        "machine",
        "machine__machine_type",
        "store",
        "assigned_to",
    )
    if user.role == User.Role.REPAIR_STAFF:
        return queryset.filter(assigned_to=user)
    return queryset.filter(store__in=stores_visible_to_user(user))


def _recent_assignment_activity(assignments):
    assignment_ids = [str(assignment.pk) for assignment in assignments]
    activity_map = defaultdict(list)
    if not assignment_ids:
        return activity_map

    logs = AuditLog.objects.filter(
        entity_type="RepairAssignment",
        entity_id__in=assignment_ids,
    ).select_related("actor")[:80]
    for log in logs:
        note = log.after_state.get("note") or log.after_state.get("notes") or ""
        activity_map[log.entity_id].append(
            {
                "label": AUDIT_LABELS.get(
                    log.action, log.action.replace("_", " ").title()
                ),
                "note": note,
                "created_at": log.created_at,
                "actor": log.actor,
            }
        )
    return activity_map


def build_route_groups(assignments):
    groups = {}
    for assignment in assignments:
        if assignment.status not in RepairAssignment.actionable_statuses():
            continue
        key = assignment.route_batch_key or route_batch_key_for_machine(
            assignment.machine
        )
        group = groups.setdefault(
            key,
            {
                "key": key,
                "label": f"{assignment.store.city}, {assignment.store.state_code}",
                "assignments": [],
                "store_names": set(),
                "assignee_names": set(),
                "highest_priority": assignment.priority_score,
                "next_stop_at": assignment.scheduled_for,
            },
        )
        group["assignments"].append(assignment)
        group["store_names"].add(assignment.store.name)
        group["assignee_names"].add(
            assignment.assigned_to.get_full_name() or assignment.assigned_to.email
        )
        if assignment.priority_score > group["highest_priority"]:
            group["highest_priority"] = assignment.priority_score
        if assignment.scheduled_for and (
            group["next_stop_at"] is None
            or assignment.scheduled_for < group["next_stop_at"]
        ):
            group["next_stop_at"] = assignment.scheduled_for

    rows = []
    for group in groups.values():
        rows.append(
            {
                "key": group["key"],
                "label": group["label"],
                "assignment_count": len(group["assignments"]),
                "store_count": len(group["store_names"]),
                "store_names": sorted(group["store_names"]),
                "assignee_names": sorted(group["assignee_names"]),
                "highest_priority": group["highest_priority"],
                "next_stop_at": group["next_stop_at"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -row["highest_priority"],
            row["next_stop_at"] or row["label"],
        ),
    )


def build_assignment_cards(user):
    assignments = list(
        _assignment_scope_queryset(user)
        .exclude(
            status__in=[
                RepairAssignment.Status.CLOSED,
                RepairAssignment.Status.CANCELED,
            ]
        )
        .order_by("scheduled_for", "-priority_score", "-updated_at")
    )
    activity_map = _recent_assignment_activity(assignments)
    for assignment in assignments:
        assignment.recent_activity = activity_map.get(str(assignment.pk), [])[:4]
    return assignments


def build_urgent_machine_rows(user, *, status_filter=""):
    visible_stores = stores_visible_to_user(user)
    machines = list(
        Machine.objects.filter(
            store__in=visible_stores,
            current_status__in=[
                Machine.Status.SCHEDULE_SERVICE,
                Machine.Status.WARNING,
                Machine.Status.ERROR,
                Machine.Status.OUT_OF_ORDER,
            ],
        )
        .select_related("store", "machine_type")
        .order_by("store__name", "display_name")
    )
    if status_filter:
        machines = [
            machine for machine in machines if machine.current_status == status_filter
        ]

    assignments = (
        RepairAssignment.objects.filter(
            machine__in=machines,
            status__in=RepairAssignment.actionable_statuses(),
        )
        .select_related("assigned_to", "store", "machine")
        .order_by("-priority_score", "scheduled_for", "-created_at")
    )
    active_assignments = {}
    for assignment in assignments:
        active_assignments.setdefault(assignment.machine_id, assignment)

    rows = []
    today = timezone.localdate()
    for machine in machines:
        assignment = active_assignments.get(machine.pk)
        rows.append(
            {
                "machine": machine,
                "assignment": assignment,
                "priority_score": calculate_machine_priority(machine),
                "explanation": explain_maintenance_priority(machine),
                "days_in_status": (
                    max((today - machine.current_status_date).days, 0)
                    if machine.current_status_date
                    else 0
                ),
                "route_batch_key": (
                    assignment.route_batch_key
                    if assignment is not None
                    else route_batch_key_for_machine(machine)
                ),
                "can_claim": user.role == User.Role.REPAIR_STAFF and assignment is None,
                "can_auto_assign": user.role
                in {User.Role.MANAGER, User.Role.ADMIN, User.Role.SUPER_ADMIN}
                and assignment is None,
            }
        )
    return sorted(
        rows, key=lambda row: (-row["priority_score"], row["machine"].store.name)
    )
