from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import notify_store_roles, notify_user
from apps.orders.models import Order
from apps.supply_hubs.models import SupplyTransfer
from apps.users.models import User

from .models import AuditLog, SyncOutboxEvent


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


def create_outbox_event(*, event_type, instance, payload=None, source_scope=None, entity_version=1):
    event = SyncOutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=instance.__class__.__name__,
        aggregate_id=str(instance.pk),
        entity_version=entity_version,
        source_scope=source_scope or {},
        payload=_serialize_value(payload or {}),
    )
    transaction.on_commit(_enqueue_outbox_processing)
    return event


def create_audit_log(*, actor=None, action, instance, before=None, after=None, store=None, region=None):
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


def _dispatch_outbox_event(event):
    if event.event_type == "order.ready":
        order = Order.objects.select_related("customer", "store").filter(pk=event.aggregate_id).first()
        if order and order.customer_id:
            notify_user(
                user=order.customer,
                title="Your order is ready",
                message=f"{order.public_order_code} is ready for pickup at {order.store.name}.",
                category=Notification.Category.TASK,
            )
    elif event.event_type == "order.refunded":
        order = Order.objects.select_related("customer").filter(pk=event.aggregate_id).first()
        if order and order.customer_id:
            notify_user(
                user=order.customer,
                title="Refund completed",
                message=f"{order.public_order_code} has been refunded.",
                category=Notification.Category.INFO,
            )
    elif event.event_type == "order.failed":
        order = Order.objects.select_related("customer").filter(pk=event.aggregate_id).first()
        if order and order.customer_id:
            notify_user(
                user=order.customer,
                title="Payment issue",
                message=f"We could not complete payment for {order.public_order_code}. Please try again.",
                category=Notification.Category.ALERT,
            )
    elif event.event_type == "transfer.approved":
        transfer = SupplyTransfer.objects.select_related("requested_by", "destination_store").filter(
            pk=event.aggregate_id
        ).first()
        if transfer:
            notify_user(
                user=transfer.requested_by,
                title="Transfer approved",
                message=f"Transfer to {transfer.destination_store.name} was approved.",
                category=Notification.Category.TASK,
            )
    elif event.event_type in {"machine.out-of-order", "machine.error"}:
        aggregate_store_id = event.source_scope.get("store_id")
        from apps.stores.models import Store

        store = Store.objects.select_related("region").filter(pk=aggregate_store_id).first()
        if store:
            notify_store_roles(
                store=store,
                roles=[User.Role.MANAGER, User.Role.ADMIN],
                title="Machine escalation",
                message=f"{store.name} has a machine in {event.event_type.split('.')[-1]} status.",
                category=Notification.Category.ALERT,
            )


def process_outbox_event(event):
    if event.status == SyncOutboxEvent.Status.DISPATCHED:
        return event

    before = serialize_instance(event)
    event.status = SyncOutboxEvent.Status.PROCESSING
    event.attempt_count += 1
    event.last_error = ""
    event.save(update_fields=["status", "attempt_count", "last_error", "updated_at"])
    try:
        _dispatch_outbox_event(event)
        event.status = SyncOutboxEvent.Status.DISPATCHED
        event.next_attempt_at = None
        event.save(update_fields=["status", "next_attempt_at", "updated_at"])
    except Exception as exc:  # pragma: no cover - defensive
        event.status = SyncOutboxEvent.Status.FAILED
        event.last_error = str(exc)
        event.next_attempt_at = timezone.now() + timedelta(minutes=5)
        event.save(update_fields=["status", "last_error", "next_attempt_at", "updated_at"])
    create_audit_log(
        action="sync.outbox_processed",
        instance=event,
        before=before,
        after=serialize_instance(event),
    )
    return event


def process_pending_outbox_events(*, limit=25):
    events = list(
        SyncOutboxEvent.objects.filter(status=SyncOutboxEvent.Status.PENDING)
        .order_by("created_at")[:limit]
    )
    for event in events:
        process_outbox_event(event)
    return len(events)


def retry_failed_outbox_events(*, limit=25):
    events = SyncOutboxEvent.objects.filter(status=SyncOutboxEvent.Status.FAILED).order_by("created_at")[:limit]
    event_ids = list(events.values_list("id", flat=True))
    if event_ids:
        SyncOutboxEvent.objects.filter(id__in=event_ids).update(
            status=SyncOutboxEvent.Status.PENDING,
            next_attempt_at=None,
            last_error="",
        )
        transaction.on_commit(_enqueue_outbox_processing)
    return len(event_ids)
