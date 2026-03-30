from __future__ import annotations

from apps.sync.services import create_audit_log
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import DeviceRegistration, Notification


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_notification_async(self, notification_id):
    notification = Notification.objects.select_related("user").get(pk=notification_id)
    devices = DeviceRegistration.objects.filter(user=notification.user, is_active=True)
    configured_providers = {
        "web_push": bool(
            getattr(settings, "WEB_PUSH_PUBLIC_KEY", "")
            and getattr(settings, "WEB_PUSH_PRIVATE_KEY", "")
        ),
        "fcm": bool(getattr(settings, "FCM_SERVER_KEY", "")),
    }
    eligible_devices = {
        "web_push": devices.filter(
            push_provider=DeviceRegistration.PushProvider.WEB_PUSH
        ).count(),
        "fcm": devices.filter(
            push_provider=DeviceRegistration.PushProvider.FCM
        ).count(),
    }
    delivery_summary = {
        "in_app": "stored",
        "configured_providers": configured_providers,
        "eligible_devices": eligible_devices,
        "delivery_channel": notification.delivery_channel,
    }
    notification.delivery_status = Notification.DeliveryStatus.SENT
    notification.sent_at = notification.sent_at or timezone.now()
    notification.save(update_fields=["delivery_status", "sent_at", "updated_at"])
    create_audit_log(
        action="notification.dispatched",
        instance=notification,
        after=delivery_summary,
    )
    return delivery_summary
