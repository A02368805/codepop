from __future__ import annotations

from celery import shared_task

from .models import SyncOutboxEvent, SyncPeerDelivery
from .services import (
    process_pending_outbox_events,
    push_event_to_peer,
    retry_failed_outbox_events,
    retry_failed_peer_deliveries,
)


@shared_task
def ping():
    return "pong"


@shared_task
def process_pending_outbox_events_async(limit=25):
    return process_pending_outbox_events(limit=limit)


@shared_task
def retry_failed_outbox_events_async(limit=25):
    return retry_failed_outbox_events(limit=limit)


@shared_task
def push_pending_peer_deliveries_async(event_id: str):
    """Push a single event to all pending peer deliveries."""
    try:
        event = SyncOutboxEvent.objects.get(pk=event_id)
    except SyncOutboxEvent.DoesNotExist:
        return

    for delivery in event.peer_deliveries.filter(
        status=SyncPeerDelivery.Status.PENDING
    ):
        push_event_to_peer(event, delivery)


@shared_task
def retry_failed_peer_deliveries_async():
    """Retry peer deliveries that are due for retry."""
    return retry_failed_peer_deliveries()
