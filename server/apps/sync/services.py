from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from apps.imports.models import ImportJob
from apps.maintenance.models import Machine, RepairAssignment
from apps.notifications.models import Notification
from apps.notifications.services import (
    notify_store_roles,
    notify_user,
    notify_users,
    users_for_region_roles,
    users_for_store_roles,
)
from apps.orders.models import Order
from apps.stores.models import Region, Store
from apps.supply_hubs.models import SupplyTransfer
from apps.users.models import User
from django.db import transaction
from django.db.models import Max
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone

from .models import AuditLog, SyncConflictLog, SyncOutboxEvent, SyncProjectionState

EVENT_STAGE_ORDER = {
    "order.created": 0,
    "order.payment_pending": 1,
    "order.paid": 2,
    "order.queued": 3,
    "order.preparing": 4,
    "order.ready": 5,
    "order.picked_up": 6,
    "order.expired": 6,
    "order.refund_pending": 7,
    "order.refunded": 8,
    "order.canceled": 8,
    "order.failed": 8,
    "transfer.requested": 0,
    "transfer.approved": 1,
    "transfer.reserved": 2,
    "transfer.shipped": 3,
    "transfer.delivered": 4,
    "transfer.received": 5,
    "repair_assignment.created": 0,
    "repair_assignment.acknowledged": 1,
    "repair_assignment.started": 2,
    "repair_assignment.updated": 2,
    "repair_assignment.blocked": 3,
    "repair_assignment.completed": 4,
    "repair_assignment.closed": 5,
    "repair_assignment.canceled": 5,
}


@dataclass(frozen=True)
class ProjectionTarget:
    scope_type: str
    scope_key: str
    label: str


class SyncProjectionConflictError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def _serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if hasattr(value, "pk"):
        return str(value.pk)
    return value


def serialize_instance(instance, *, fields=None):
    if instance is None:
        return {}
    payload = model_to_dict(instance, fields=fields)
    payload["pk"] = str(instance.pk)
    return _serialize_value(payload)


def _next_entity_version(instance) -> int:
    latest_version = (
        SyncOutboxEvent.objects.filter(
            aggregate_type=instance.__class__.__name__,
            aggregate_id=str(instance.pk),
        ).aggregate(max_version=Max("entity_version"))["max_version"]
        or 0
    )
    return latest_version + 1


def create_outbox_event(
    *, event_type, instance, payload=None, source_scope=None, entity_version=None
):
    event = SyncOutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=instance.__class__.__name__,
        aggregate_id=str(instance.pk),
        entity_version=entity_version or _next_entity_version(instance),
        source_scope=_serialize_value(source_scope or {}),
        payload=_serialize_value(payload or {}),
    )
    transaction.on_commit(_enqueue_outbox_processing)
    return event


def create_audit_log(
    *, actor=None, action, instance, before=None, after=None, store=None, region=None
):
    resolved_store = store or getattr(instance, "store", None)
    resolved_region = region or getattr(instance, "region", None)
    if resolved_region is None and resolved_store is not None:
        resolved_region = getattr(resolved_store, "region", None)

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=instance.__class__.__name__,
        entity_id=str(instance.pk),
        store=resolved_store,
        region=resolved_region,
        before_state=_serialize_value(before or {}),
        after_state=_serialize_value(after or {}),
    )


def _enqueue_outbox_processing():
    from .tasks import process_pending_outbox_events_async

    process_pending_outbox_events_async.delay(25)


def _receiver_label(scope_type: str, scope_key: str) -> str:
    if scope_type == SyncProjectionState.ReceiverScope.REGION:
        region = Region.objects.filter(code=scope_key).only("code", "name").first()
        return region.name if region else f"Region {scope_key}"
    if scope_type == SyncProjectionState.ReceiverScope.STORE:
        store = Store.objects.filter(pk=scope_key).only("store_code", "name").first()
        return store.name if store else f"Store {scope_key}"
    return "Super Admin Oversight"


def _required_source_scope_keys(event: SyncOutboxEvent) -> set[str]:
    aggregate_requirements = {
        "Order": {"store_id", "region_code"},
        "Machine": {"store_id", "region_code"},
        "RepairAssignment": {"store_id", "region_code"},
        "SupplyTransfer": {"region_code"},
        "SupplierReplenishment": {"region_code"},
    }
    return aggregate_requirements.get(event.aggregate_type, set())


def _log_sync_conflict(
    *,
    event: SyncOutboxEvent,
    target: ProjectionTarget,
    conflict_type: str,
    message: str,
    details=None,
    resolution_status=SyncConflictLog.ResolutionStatus.OPEN,
):
    conflict = SyncConflictLog.objects.create(
        outbox_event=event,
        receiver_scope_type=target.scope_type,
        receiver_scope_key=target.scope_key,
        receiver_label=target.label,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        conflict_type=conflict_type,
        resolution_status=resolution_status,
        message=message,
        details=_serialize_value(details or {}),
        resolved_at=(
            timezone.now()
            if resolution_status != SyncConflictLog.ResolutionStatus.OPEN
            else None
        ),
    )
    create_audit_log(
        action="sync.conflict_logged",
        instance=conflict,
        after=serialize_instance(conflict),
    )
    return conflict


def resolve_sync_conflict(conflict, *, resolution_status):
    if resolution_status not in {
        SyncConflictLog.ResolutionStatus.RESOLVED,
        SyncConflictLog.ResolutionStatus.IGNORED,
    }:
        raise ValueError("Unsupported sync conflict resolution status.")
    conflict.resolution_status = resolution_status
    conflict.resolved_at = timezone.now()
    conflict.save(update_fields=["resolution_status", "resolved_at"])
    create_audit_log(
        action="sync.conflict_resolved",
        instance=conflict,
        after=serialize_instance(conflict),
    )
    return conflict


def _projection_targets_for_event(event: SyncOutboxEvent) -> list[ProjectionTarget]:
    targets = {}
    source_scope = event.source_scope or {}

    def add(scope_type: str, scope_key: str):
        if not scope_key:
            return
        targets[(scope_type, scope_key)] = ProjectionTarget(
            scope_type=scope_type,
            scope_key=scope_key,
            label=_receiver_label(scope_type, scope_key),
        )

    add(
        SyncProjectionState.ReceiverScope.STORE,
        source_scope.get("store_id", ""),
    )
    add(
        SyncProjectionState.ReceiverScope.REGION,
        source_scope.get("region_code", ""),
    )

    if event.aggregate_type == "SupplyTransfer":
        transfer = (
            SupplyTransfer.objects.select_related(
                "destination_store",
                "destination_store__region",
                "source_store",
                "source_store__region",
                "source_hub",
                "source_hub__region",
            )
            .filter(pk=event.aggregate_id)
            .first()
        )
        if transfer is not None:
            add(
                SyncProjectionState.ReceiverScope.STORE,
                str(transfer.destination_store_id),
            )
            add(
                SyncProjectionState.ReceiverScope.REGION,
                transfer.destination_store.region.code,
            )
            if transfer.source_store_id:
                add(
                    SyncProjectionState.ReceiverScope.REGION,
                    transfer.source_store.region.code,
                )
            if transfer.source_hub_id:
                add(
                    SyncProjectionState.ReceiverScope.REGION,
                    transfer.source_hub.region.code,
                )

    add(SyncProjectionState.ReceiverScope.GLOBAL, "super_admin")
    return list(targets.values())


def _validate_projection_scope(
    event: SyncOutboxEvent,
    *,
    target: ProjectionTarget,
    projection=None,
):
    source_scope = event.source_scope or {}
    required_keys = _required_source_scope_keys(event)
    missing_keys = sorted(key for key in required_keys if not source_scope.get(key))
    if missing_keys:
        _log_sync_conflict(
            event=event,
            target=target,
            conflict_type=SyncConflictLog.ConflictType.INVALID_SCOPE,
            message=f"Event is missing required scope keys: {', '.join(missing_keys)}.",
            details={
                "required_keys": missing_keys,
                "source_scope": source_scope,
            },
        )
        raise SyncProjectionConflictError("Event scope is incomplete for sync.")

    if projection is None:
        return

    projection_scope = projection.source_scope or {}
    for scope_key in ("store_id", "region_code"):
        projected_value = projection_scope.get(scope_key)
        incoming_value = source_scope.get(scope_key)
        if projected_value and incoming_value and projected_value != incoming_value:
            _log_sync_conflict(
                event=event,
                target=target,
                conflict_type=SyncConflictLog.ConflictType.OWNERSHIP_MISMATCH,
                message=(
                    f"Incoming event scope for {scope_key} does not match the "
                    f"existing projection owner."
                ),
                details={
                    "scope_key": scope_key,
                    "existing_value": projected_value,
                    "incoming_value": incoming_value,
                },
            )
            raise SyncProjectionConflictError("Event owner does not match receiver.")


def _validate_transition(
    event: SyncOutboxEvent, *, projection, target: ProjectionTarget
):
    previous_stage = EVENT_STAGE_ORDER.get(projection.last_event_type)
    incoming_stage = EVENT_STAGE_ORDER.get(event.event_type)
    if previous_stage is None or incoming_stage is None:
        return
    if incoming_stage < previous_stage:
        _log_sync_conflict(
            event=event,
            target=target,
            conflict_type=SyncConflictLog.ConflictType.INVALID_TRANSITION,
            message=(
                f"Incoming event {event.event_type} regresses the receiver from "
                f"{projection.last_event_type}."
            ),
            details={
                "previous_event_type": projection.last_event_type,
                "incoming_event_type": event.event_type,
                "previous_stage": previous_stage,
                "incoming_stage": incoming_stage,
            },
        )
        raise SyncProjectionConflictError("Event transition is stale or invalid.")


def _apply_event_to_projection(
    event: SyncOutboxEvent, *, target: ProjectionTarget
) -> bool:
    projection = SyncProjectionState.objects.filter(
        receiver_scope_type=target.scope_type,
        receiver_scope_key=target.scope_key,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
    ).first()

    _validate_projection_scope(event, target=target, projection=projection)

    if projection is not None:
        if event.entity_version < projection.last_entity_version:
            _log_sync_conflict(
                event=event,
                target=target,
                conflict_type=SyncConflictLog.ConflictType.STALE_EVENT,
                message=(
                    f"Event version {event.entity_version} is older than the "
                    f"receiver version {projection.last_entity_version}."
                ),
                details={
                    "receiver_version": projection.last_entity_version,
                    "event_version": event.entity_version,
                    "last_event_type": projection.last_event_type,
                },
                resolution_status=SyncConflictLog.ResolutionStatus.IGNORED,
            )
            return False
        if (
            event.entity_version == projection.last_entity_version
            and projection.last_event_type == event.event_type
        ):
            _log_sync_conflict(
                event=event,
                target=target,
                conflict_type=SyncConflictLog.ConflictType.STALE_EVENT,
                message="Duplicate event was ignored because this receiver already applied it.",
                details={"event_type": event.event_type},
                resolution_status=SyncConflictLog.ResolutionStatus.IGNORED,
            )
            return False
        _validate_transition(event, projection=projection, target=target)

    before = serialize_instance(projection) if projection is not None else {}
    if projection is None:
        projection = SyncProjectionState.objects.create(
            receiver_scope_type=target.scope_type,
            receiver_scope_key=target.scope_key,
            receiver_label=target.label,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            last_event_type=event.event_type,
            last_entity_version=event.entity_version,
            source_scope=event.source_scope,
            payload_snapshot=event.payload,
        )
    else:
        projection.receiver_label = target.label
        projection.last_event_type = event.event_type
        projection.last_entity_version = event.entity_version
        projection.source_scope = event.source_scope
        projection.payload_snapshot = event.payload
        projection.save(
            update_fields=[
                "receiver_label",
                "last_event_type",
                "last_entity_version",
                "source_scope",
                "payload_snapshot",
                "updated_at",
            ]
        )
    create_audit_log(
        action="sync.projection_applied",
        instance=projection,
        before=before,
        after=serialize_instance(projection),
    )
    return True


def _apply_event_to_receivers(event: SyncOutboxEvent) -> bool:
    any_applied = False
    for target in _projection_targets_for_event(event):
        any_applied = _apply_event_to_projection(event, target=target) or any_applied
    return any_applied


def _order_notification_payload(order):
    return {
        "action_url": reverse("orders:detail", args=[order.public_order_code]),
        "order_code": order.public_order_code,
        "store_name": order.store.name,
    }


def _maintenance_notification_payload(*, machine=None, assignment=None):
    payload = {
        "action_url": reverse("maintenance:index"),
    }
    if machine is not None:
        payload.update(
            {
                "machine_id": str(machine.pk),
                "machine_name": machine.display_name,
                "store_name": machine.store.name,
            }
        )
    if assignment is not None:
        payload.update(
            {
                "assignment_id": str(assignment.pk),
                "machine_id": str(assignment.machine_id),
                "machine_name": assignment.machine.display_name,
                "store_name": assignment.store.name,
                "route_batch_key": assignment.route_batch_key,
            }
        )
    return payload


def _transfer_notification_recipients(transfer):
    recipient_ids = set()
    if transfer.requested_by_id:
        recipient_ids.add(transfer.requested_by_id)

    recipient_ids.update(
        users_for_store_roles(
            transfer.destination_store,
            [User.Role.MANAGER, User.Role.ADMIN],
        ).values_list("pk", flat=True)
    )
    recipient_ids.update(
        users_for_region_roles(
            transfer.destination_store.region,
            [User.Role.LOGISTICS_MANAGER],
        ).values_list("pk", flat=True)
    )
    if transfer.source_store_id:
        recipient_ids.update(
            users_for_store_roles(
                transfer.source_store,
                [User.Role.MANAGER, User.Role.ADMIN],
            ).values_list("pk", flat=True)
        )
        if transfer.source_store.region_id != transfer.destination_store.region_id:
            recipient_ids.update(
                users_for_region_roles(
                    transfer.source_store.region,
                    [User.Role.LOGISTICS_MANAGER],
                ).values_list("pk", flat=True)
            )
    if (
        transfer.source_hub_id
        and transfer.source_hub.region_id != transfer.destination_store.region_id
    ):
        recipient_ids.update(
            users_for_region_roles(
                transfer.source_hub.region,
                [User.Role.LOGISTICS_MANAGER],
            ).values_list("pk", flat=True)
        )
    return User.objects.filter(pk__in=recipient_ids)


def _notify_order_event(event):
    order = (
        Order.objects.select_related("customer", "store")
        .filter(pk=event.aggregate_id)
        .first()
    )
    if not order or not order.customer_id:
        return

    payload = _order_notification_payload(order)
    if event.event_type == "order.ready":
        notify_user(
            user=order.customer,
            title="Your order is ready",
            message=f"{order.public_order_code} is ready for pickup at {order.store.name}.",
            category=Notification.Category.TASK,
            notification_type=Notification.NotificationType.ORDER_UPDATE,
            payload_json=payload,
        )
    elif event.event_type == "order.refunded":
        notify_user(
            user=order.customer,
            title="Refund completed",
            message=f"{order.public_order_code} has been refunded.",
            category=Notification.Category.INFO,
            notification_type=Notification.NotificationType.ORDER_UPDATE,
            payload_json=payload,
        )
    elif event.event_type == "order.failed":
        notify_user(
            user=order.customer,
            title="Payment issue",
            message=f"We could not complete payment for {order.public_order_code}. Please try again.",
            category=Notification.Category.ALERT,
            notification_type=Notification.NotificationType.ORDER_UPDATE,
            payload_json=payload,
        )


def _notify_import_event(event):
    job = (
        ImportJob.objects.select_related("uploaded_by")
        .filter(pk=event.aggregate_id)
        .first()
    )
    if not job or not job.uploaded_by_id:
        return

    succeeded = event.event_type.endswith("succeeded")
    title = "Import completed" if succeeded else "Import failed"
    message = (
        f"{job.original_filename} finished with {job.success_count} successful row(s)."
        if succeeded
        else f"{job.original_filename} failed validation. Review the import history panel for details."
    )
    notify_user(
        user=job.uploaded_by,
        title=title,
        message=message,
        category=(
            Notification.Category.INFO if succeeded else Notification.Category.ALERT
        ),
        notification_type=Notification.NotificationType.IMPORT_RESULT,
        payload_json={
            "action_url": reverse("imports:index"),
            "import_type": job.import_type,
            "status": job.status,
            "original_filename": job.original_filename,
        },
    )


def _notify_transfer_event(event):
    transfer = (
        SupplyTransfer.objects.select_related(
            "requested_by",
            "destination_store",
            "destination_store__region",
            "source_store",
            "source_store__region",
            "source_hub",
            "source_hub__region",
        )
        .filter(pk=event.aggregate_id)
        .first()
    )
    if transfer is None:
        return

    labels = {
        "transfer.requested": "requested",
        "transfer.approved": "approved",
        "transfer.reserved": "reserved",
        "transfer.shipped": "shipped",
        "transfer.delivered": "delivered",
        "transfer.received": "received",
    }
    status_label = labels[event.event_type]
    source_name = (
        transfer.source_store.name
        if transfer.source_store_id
        else transfer.source_hub.name
    )
    recipients = _transfer_notification_recipients(transfer)
    notify_users(
        users=recipients,
        title=f"Transfer {status_label.title()}",
        message=(
            f"{source_name} -> {transfer.destination_store.name} is now {status_label}."
        ),
        category=(
            Notification.Category.TASK
            if event.event_type in {"transfer.requested", "transfer.approved"}
            else Notification.Category.INFO
        ),
        notification_type=Notification.NotificationType.TRANSFER_UPDATE,
        payload_json={
            "action_url": reverse("supply_hubs:index"),
            "transfer_id": str(transfer.pk),
            "status": transfer.status,
            "destination_store": transfer.destination_store.name,
        },
    )


def _notify_machine_event(event):
    machine = (
        Machine.objects.select_related("store", "store__region", "machine_type")
        .filter(pk=event.aggregate_id)
        .first()
    )
    if machine is None:
        return

    payload = _maintenance_notification_payload(machine=machine)
    if event.event_type == "machine.schedule-service":
        notify_store_roles(
            store=machine.store,
            roles=[User.Role.REPAIR_STAFF, User.Role.MANAGER, User.Role.ADMIN],
            title="Preventive service window opened",
            message=f"{machine.display_name} entered the scheduled service window at {machine.store.name}.",
            category=Notification.Category.TASK,
            notification_type=Notification.NotificationType.MACHINE_ALERT,
            payload_json=payload,
        )
        return

    titles = {
        "machine.warning": "Machine warning",
        "machine.error": "Machine escalation",
        "machine.out-of-order": "Machine out of order",
    }
    notify_store_roles(
        store=machine.store,
        roles=[User.Role.REPAIR_STAFF, User.Role.MANAGER, User.Role.ADMIN],
        title=titles[event.event_type],
        message=(
            f"{machine.display_name} at {machine.store.name} is now "
            f"{machine.get_current_status_display().lower()}."
        ),
        category=(
            Notification.Category.ALERT
            if event.event_type in {"machine.error", "machine.out-of-order"}
            else Notification.Category.TASK
        ),
        notification_type=Notification.NotificationType.MACHINE_ALERT,
        payload_json=payload,
    )


def _notify_repair_assignment_event(event):
    assignment = (
        RepairAssignment.objects.select_related(
            "assigned_to",
            "machine",
            "store",
            "store__region",
        )
        .filter(pk=event.aggregate_id)
        .first()
    )
    if assignment is None:
        return

    payload = _maintenance_notification_payload(assignment=assignment)
    event_note = event.payload.get("note", "")

    if event.event_type == "repair_assignment.created":
        notify_user(
            user=assignment.assigned_to,
            title="Repair assignment created",
            message=(
                f"{assignment.machine.display_name} at {assignment.store.name} "
                f"was assigned to your queue."
            ),
            category=Notification.Category.TASK,
            notification_type=Notification.NotificationType.REPAIR_ASSIGNMENT,
            payload_json=payload,
        )
        return

    titles = {
        "repair_assignment.acknowledged": "Repair visit acknowledged",
        "repair_assignment.started": "Repair visit started",
        "repair_assignment.blocked": "Repair visit blocked",
        "repair_assignment.updated": "Repair update posted",
        "repair_assignment.completed": "Repair visit completed",
        "repair_assignment.closed": "Repair assignment closed",
        "repair_assignment.canceled": "Repair assignment canceled",
    }
    message = (
        f"{assignment.machine.display_name} at {assignment.store.name} is now "
        f"{assignment.get_status_display().lower()}."
    )
    if event_note:
        message = f"{message} Note: {event_note}"

    notify_store_roles(
        store=assignment.store,
        roles=[User.Role.MANAGER, User.Role.ADMIN],
        title=titles[event.event_type],
        message=message,
        category=(
            Notification.Category.ALERT
            if event.event_type == "repair_assignment.blocked"
            else Notification.Category.INFO
        ),
        notification_type=Notification.NotificationType.REPAIR_ASSIGNMENT,
        payload_json=payload,
    )


def _dispatch_outbox_event(event):
    if event.event_type in {"order.ready", "order.refunded", "order.failed"}:
        _notify_order_event(event)
        return
    if event.event_type.startswith("import."):
        _notify_import_event(event)
        return
    if event.event_type.startswith("transfer."):
        _notify_transfer_event(event)
        return
    if event.event_type.startswith("machine."):
        _notify_machine_event(event)
        return
    if event.event_type.startswith("repair_assignment."):
        _notify_repair_assignment_event(event)


def process_outbox_event(event):
    if event.status == SyncOutboxEvent.Status.DISPATCHED:
        return event

    before = serialize_instance(event)
    event.status = SyncOutboxEvent.Status.PROCESSING
    event.attempt_count += 1
    event.last_error = ""
    event.save(update_fields=["status", "attempt_count", "last_error", "updated_at"])
    try:
        should_dispatch_notifications = _apply_event_to_receivers(event)
        if should_dispatch_notifications:
            _dispatch_outbox_event(event)
        event.status = SyncOutboxEvent.Status.DISPATCHED
        event.next_attempt_at = None
        event.save(update_fields=["status", "next_attempt_at", "updated_at"])
        # Queue peer push after local processing succeeds
        try:
            _enqueue_peer_push(event)
        except Exception:
            pass  # Peer push failure must not roll back local success
    except SyncProjectionConflictError as exc:
        event.status = SyncOutboxEvent.Status.FAILED
        event.last_error = str(exc)
        event.next_attempt_at = timezone.now() + timedelta(minutes=15)
        event.save(
            update_fields=["status", "last_error", "next_attempt_at", "updated_at"]
        )
    except Exception as exc:  # pragma: no cover - defensive
        event.status = SyncOutboxEvent.Status.FAILED
        event.last_error = str(exc)
        event.next_attempt_at = timezone.now() + timedelta(minutes=5)
        event.save(
            update_fields=["status", "last_error", "next_attempt_at", "updated_at"]
        )
    create_audit_log(
        action="sync.outbox_processed",
        instance=event,
        before=before,
        after=serialize_instance(event),
    )
    return event


def process_pending_outbox_events(*, limit=25):
    events = list(
        SyncOutboxEvent.objects.filter(status=SyncOutboxEvent.Status.PENDING).order_by(
            "created_at"
        )[:limit]
    )
    for event in events:
        process_outbox_event(event)
    return len(events)


def retry_failed_outbox_events(*, limit=25):
    events = SyncOutboxEvent.objects.filter(
        status=SyncOutboxEvent.Status.FAILED
    ).order_by("created_at")[:limit]
    event_ids = list(events.values_list("id", flat=True))
    if event_ids:
        SyncOutboxEvent.objects.filter(id__in=event_ids).update(
            status=SyncOutboxEvent.Status.PENDING,
            next_attempt_at=None,
            last_error="",
        )
        transaction.on_commit(_enqueue_outbox_processing)
    return len(event_ids)


# --- Peer sync / distributed transport layer ---


def _enqueue_peer_push(event: SyncOutboxEvent) -> None:
    """Schedule peer push task if sync is enabled."""
    from apps.sync.tasks import push_pending_peer_deliveries_async
    from django.conf import settings

    if not settings.SYNC_PUSH_ENABLED or event.origin_node_id != "":
        return

    # Create peer delivery records
    push_event_to_all_peers(event)

    # Queue async task to send them
    transaction.on_commit(
        lambda: push_pending_peer_deliveries_async.delay(str(event.pk))
    )


def push_event_to_peer(event: SyncOutboxEvent, delivery) -> None:
    """
    POST an outbox event to a peer node's ingest endpoint.
    Updates delivery status and retry metadata.
    """
    from datetime import timedelta

    import requests
    from django.conf import settings

    try:
        payload = {
            "event_id": str(event.pk),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "entity_version": event.entity_version,
            "source_scope": event.source_scope,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }

        response = requests.post(
            f"{delivery.peer_url}/sync/ingest/",
            json=payload,
            headers={
                "X-Sync-Token": settings.SYNC_API_SECRET,
                "X-Origin-Node": settings.STORE_ID,
            },
            timeout=10,
        )
        response.raise_for_status()

        # Success: mark delivered
        delivery.status = "delivered"
        delivery.save(update_fields=["status", "updated_at"])

    except Exception as exc:
        # Failure: increment attempt and schedule retry with backoff
        delivery.attempt_count += 1
        delivery.status = "failed"
        delivery.last_error = str(exc)[:500]

        # Exponential backoff: 1min, 5min, 15min, then daily
        backoff_seconds = [60, 300, 900, 86400]
        seconds = backoff_seconds[
            min(delivery.attempt_count - 1, len(backoff_seconds) - 1)
        ]
        delivery.next_attempt_at = timezone.now() + timedelta(seconds=seconds)

        delivery.save(
            update_fields=[
                "attempt_count",
                "status",
                "last_error",
                "next_attempt_at",
                "updated_at",
            ]
        )


def push_event_to_all_peers(event: SyncOutboxEvent) -> None:
    """
    Create peer delivery records and queue async push for all configured peers.
    Only runs if SYNC_PUSH_ENABLED and event was created locally (origin_node_id == "").
    """
    from apps.sync.models import SyncPeerDelivery
    from django.conf import settings

    if not settings.SYNC_PUSH_ENABLED or event.origin_node_id != "":
        return

    for peer_node_id, peer_url in settings.PEER_STORES.items():
        SyncPeerDelivery.objects.get_or_create(
            event=event,
            peer_node_id=peer_node_id,
            defaults={"peer_url": peer_url, "status": SyncPeerDelivery.Status.PENDING},
        )


def ingest_event_from_peer(payload: dict, *, origin_node_id: str) -> SyncOutboxEvent:
    """
    Receive and process a sync event from a peer node.
    Returns the locally-created SyncOutboxEvent (idempotent on remote_event_id).
    """
    import uuid as uuid_module

    remote_event_id = uuid_module.UUID(payload["event_id"])

    # Idempotency: skip if already ingested
    existing = SyncOutboxEvent.objects.filter(
        origin_node_id=origin_node_id,
        remote_event_id=remote_event_id,
    ).first()
    if existing:
        return existing

    # Create the event locally with peer origin marker
    event = SyncOutboxEvent.objects.create(
        event_type=payload["event_type"],
        aggregate_type=payload["aggregate_type"],
        aggregate_id=payload["aggregate_id"],
        entity_version=payload["entity_version"],
        source_scope=payload["source_scope"],
        payload=payload["payload"],
        origin_node_id=origin_node_id,
        remote_event_id=remote_event_id,
    )

    # Process the event locally (projects, conflicts, notifications)
    process_outbox_event(event)

    return event


def retry_failed_peer_deliveries() -> int:
    """Retry failed peer deliveries due for retry."""
    from apps.sync.models import SyncPeerDelivery

    now = timezone.now()
    deliveries = SyncPeerDelivery.objects.filter(
        status=SyncPeerDelivery.Status.FAILED,
        next_attempt_at__lte=now,
    ).select_related("event")[:50]

    count = 0
    for delivery in deliveries:
        delivery.status = SyncPeerDelivery.Status.PENDING
        delivery.save(update_fields=["status"])
        push_event_to_peer(delivery.event, delivery)
        count += 1

    return count
