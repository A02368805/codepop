from __future__ import annotations

from apps.users.models import User
from django.db import transaction
from django.db.models import Q

from .models import Notification


def create_notification(*, user, title, message, category=Notification.Category.INFO):
    if user is None:
        return None
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
    )
    from .tasks import dispatch_notification_async

    transaction.on_commit(
        lambda: dispatch_notification_async.delay(str(notification.pk))
    )
    return notification


def notify_user(*, user, title, message, category=Notification.Category.INFO):
    return create_notification(
        user=user,
        title=title,
        message=message,
        category=category,
    )


def notify_users(*, users, title, message, category=Notification.Category.INFO):
    notifications = []
    for user in users.distinct():
        notification = create_notification(
            user=user,
            title=title,
            message=message,
            category=category,
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
    *, store, roles, title, message, category=Notification.Category.ALERT
):
    return notify_users(
        users=users_for_store_roles(store, roles),
        title=title,
        message=message,
        category=category,
    )


def notify_region_roles(
    *, region, roles, title, message, category=Notification.Category.ALERT
):
    return notify_users(
        users=users_for_region_roles(region, roles),
        title=title,
        message=message,
        category=category,
    )
