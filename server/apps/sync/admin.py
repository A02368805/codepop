from django.contrib import admin

from .models import AuditLog, SyncConflictLog, SyncOutboxEvent, SyncProjectionState


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


@admin.register(SyncProjectionState)
class SyncProjectionStateAdmin(admin.ModelAdmin):
    list_display = (
        "receiver_label",
        "aggregate_type",
        "aggregate_id",
        "last_event_type",
        "last_entity_version",
        "updated_at",
    )
    list_filter = ("receiver_scope_type", "aggregate_type")
    search_fields = ("receiver_label", "aggregate_type", "aggregate_id")


@admin.register(SyncConflictLog)
class SyncConflictLogAdmin(admin.ModelAdmin):
    list_display = (
        "receiver_label",
        "aggregate_type",
        "aggregate_id",
        "conflict_type",
        "resolution_status",
        "created_at",
    )
    list_filter = ("conflict_type", "resolution_status", "receiver_scope_type")
    search_fields = ("receiver_label", "aggregate_type", "aggregate_id", "message")
