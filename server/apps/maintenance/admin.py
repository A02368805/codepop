from django.contrib import admin

from .models import (
    Machine,
    MachineStatusEvent,
    MachineType,
    MaintenancePolicy,
    RepairAssignment,
)


class MachineStatusEventInline(admin.TabularInline):
    model = MachineStatusEvent
    extra = 0


@admin.register(MachineType)
class MachineTypeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "default_service_interval_days",
        "warning_max_operational_days",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = (
        "machine_uid",
        "display_name",
        "store",
        "machine_type",
        "current_status",
        "current_status_date",
    )
    list_filter = ("current_status", "store__region", "machine_type")
    search_fields = ("display_name", "machine_uid", "store__store_code")
    inlines = [MachineStatusEventInline]


@admin.register(MachineStatusEvent)
class MachineStatusEventAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "status",
        "status_date",
        "source_import_job",
        "created_at",
    )
    list_filter = ("status", "status_date")
    search_fields = ("machine__machine_uid", "machine__display_name")


@admin.register(RepairAssignment)
class RepairAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "assigned_to",
        "store",
        "priority_score",
        "status",
        "scheduled_for",
        "follow_up_required",
    )
    list_filter = ("status", "store__region")
    search_fields = (
        "machine__machine_uid",
        "assigned_to__email",
        "store__store_code",
        "route_batch_key",
        "blocker_summary",
    )


@admin.register(MaintenancePolicy)
class MaintenancePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "machine_type",
        "region",
        "max_days_between_service",
        "warning_shutdown_days",
        "is_active",
    )
    list_filter = ("is_active", "region")
