from __future__ import annotations

from apps.imports.models import ImportJob
from apps.inventory.models import SupplyUsageRecord
from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.users.models import User
from celery import shared_task
from django.db.models import Sum

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


@shared_task
def analyze_supply_usage_import(import_job_id):
    job = (
        ImportJob.objects.select_related("uploaded_by").filter(pk=import_job_id).first()
    )
    if job is None or job.import_type != ImportJob.ImportType.SUPPLY_USAGE:
        return None
    if job.uploaded_by_id is None:
        return None

    usage_rows = SupplyUsageRecord.objects.filter(source_import_job=job)
    if not usage_rows.exists():
        return None

    totals = usage_rows.aggregate(total_used=Sum("quantity_used"))
    top_store = (
        usage_rows.values("store__name")
        .annotate(total=Sum("quantity_used"))
        .order_by("-total")
        .first()
    )
    top_store_name = top_store["store__name"] if top_store else "Unknown store"
    total_used = totals["total_used"] or 0

    return notify_user(
        user=job.uploaded_by,
        title="Import AI analysis ready",
        message=(
            f"{job.original_filename}: analyzed {job.success_count} row(s), "
            f"total usage {total_used}. Highest usage store: {top_store_name}."
        ),
        category=Notification.Category.INFO,
    )
