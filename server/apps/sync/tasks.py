from __future__ import annotations

from celery import shared_task

from .services import process_pending_outbox_events, retry_failed_outbox_events


@shared_task
def ping():
    return "pong"


@shared_task
def process_pending_outbox_events_async(limit=25):
    return process_pending_outbox_events(limit=limit)


@shared_task
def retry_failed_outbox_events_async(limit=25):
    return retry_failed_outbox_events(limit=limit)
