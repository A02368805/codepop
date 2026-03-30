from __future__ import annotations

from apps.users.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import DeviceRegistration, Notification


def create_notification(
    *,
    user,
    title,
    message,
    category=Notification.Category.INFO,
    notification_type=Notification.NotificationType.GENERIC,
    payload_json=None,
    delivery_channel=Notification.DeliveryChannel.IN_APP,
):
    if user is None:
        return None
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
        notification_type=notification_type,
        payload_json=payload_json or {},
        delivery_channel=delivery_channel,
        delivery_status=Notification.DeliveryStatus.PENDING,
    )
    from .tasks import dispatch_notification_async

    transaction.on_commit(
        lambda: dispatch_notification_async.delay(str(notification.pk))
    )
    return notification


def notify_user(
    *,
    user,
    title,
    message,
    category=Notification.Category.INFO,
    notification_type=Notification.NotificationType.GENERIC,
    payload_json=None,
    delivery_channel=Notification.DeliveryChannel.IN_APP,
):
    return create_notification(
        user=user,
        title=title,
        message=message,
        category=category,
        notification_type=notification_type,
        payload_json=payload_json,
        delivery_channel=delivery_channel,
    )


def notify_users(
    *,
    users,
    title,
    message,
    category=Notification.Category.INFO,
    notification_type=Notification.NotificationType.GENERIC,
    payload_json=None,
    delivery_channel=Notification.DeliveryChannel.IN_APP,
):
    notifications = []
    if hasattr(users, "distinct"):
        user_iterable = users.distinct()
    else:
        seen = set()
        user_iterable = []
        for user in users:
            if user.pk in seen:
                continue
            seen.add(user.pk)
            user_iterable.append(user)
    for user in user_iterable:
        notification = create_notification(
            user=user,
            title=title,
            message=message,
            category=category,
            notification_type=notification_type,
            payload_json=payload_json,
            delivery_channel=delivery_channel,
        )
        if notification is not None:
            notifications.append(notification)
    return notifications


def users_for_store_roles(store, roles):
    return User.objects.filter(
        Q(store_assignments__store=store) | Q(preferred_store=store),
        role__in=roles,
        status=User.Status.ACTIVE,
    ).distinct()


def users_for_region_roles(region, roles):
    return User.objects.filter(
        Q(region_assignments__region=region) | Q(default_region=region),
        role__in=roles,
        status=User.Status.ACTIVE,
    ).distinct()


def notify_store_roles(
    *,
    store,
    roles,
    title,
    message,
    category=Notification.Category.ALERT,
    notification_type=Notification.NotificationType.GENERIC,
    payload_json=None,
):
    return notify_users(
        users=users_for_store_roles(store, roles),
        title=title,
        message=message,
        category=category,
        notification_type=notification_type,
        payload_json=payload_json,
    )


def notify_region_roles(
    *,
    region,
    roles,
    title,
    message,
    category=Notification.Category.ALERT,
    notification_type=Notification.NotificationType.GENERIC,
    payload_json=None,
):
    return notify_users(
        users=users_for_region_roles(region, roles),
        title=title,
        message=message,
        category=category,
        notification_type=notification_type,
        payload_json=payload_json,
    )


def register_device(
    *,
    user,
    device_token,
    platform=DeviceRegistration.Platform.WEB,
    push_provider=DeviceRegistration.PushProvider.WEB_PUSH,
    device_label="",
):
    return DeviceRegistration.objects.update_or_create(
        device_token=device_token,
        defaults={
            "user": user,
            "platform": platform,
            "push_provider": push_provider,
            "device_label": device_label,
            "is_active": True,
            "last_seen_at": timezone.now(),
        },
    )[0]
