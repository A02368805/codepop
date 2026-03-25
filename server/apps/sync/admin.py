from django.contrib import admin

from .models import AuditLog, SyncOutboxEvent


@admin.register(SyncOutboxEvent)
class SyncOutboxEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "status",
        "attempt_count",
        "created_at",
    )
    list_filter = ("status", "aggregate_type")
    search_fields = ("event_type", "aggregate_id")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "entity_type",
        "entity_id",
        "actor",
        "store",
        "region",
        "created_at",
    )
    list_filter = ("action", "region")
    search_fields = ("entity_type", "entity_id", "actor__email")
