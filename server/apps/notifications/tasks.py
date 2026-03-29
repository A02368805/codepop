from __future__ import annotations

from apps.sync.services import create_audit_log
from celery import shared_task
from django.conf import settings

from .models import Notification


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_notification_async(self, notification_id):
    notification = Notification.objects.select_related("user").get(pk=notification_id)
    delivery_summary = {
        "in_app": "stored",
        "web_push": (
            "configured" if getattr(settings, "WEB_PUSH_PUBLIC_KEY", "") else "disabled"
        ),
        "fcm": "configured" if getattr(settings, "FCM_SERVER_KEY", "") else "disabled",
    }
    create_audit_log(
        action="notification.dispatched",
        instance=notification,
        after=delivery_summary,
    )
    return delivery_summary
