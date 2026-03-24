from __future__ import annotations

from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.users.models import User

from .recommendations import recommend_drinks_for_user


@shared_task
def refresh_account_recommendations(user_id, *, reason=""):
    user = User.objects.filter(pk=user_id, role=User.Role.ACCOUNT_USER).first()
    if user is None:
        return None

    recommendations = recommend_drinks_for_user(user, limit=2)
    if not recommendations:
        return None

    names = ", ".join(item["name"] for item in recommendations)
    explanation = recommendations[0]["explanation"]
    return notify_user(
        user=user,
        title="Fresh drink ideas",
        message=f"{reason or 'Your profile changed'}: try {names}. {explanation}",
        category=Notification.Category.INFO,
    )
