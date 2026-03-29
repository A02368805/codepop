from django.contrib import admin

from .models import (
    InventoryItem,
    LocalSupplier,
    RestockAlert,
    StoreInventoryBalance,
    SupplierReplenishment,
    SupplySchedule,
    SupplyUsageRecord,
)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "unit_of_measure", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")


@admin.register(StoreInventoryBalance)
class StoreInventoryBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "store",
        "inventory_item",
        "on_hand_quantity",
        "reserved_quantity",
        "reorder_threshold",
    )
    list_filter = ("store__region", "store")
    search_fields = ("store__store_code", "inventory_item__sku", "inventory_item__name")


@admin.register(LocalSupplier)
class LocalSupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "service_region", "contact_name", "is_active")
    list_filter = ("service_region", "is_active")
    search_fields = ("name", "contact_name", "email")


@admin.register(SupplierReplenishment)
class SupplierReplenishmentAdmin(admin.ModelAdmin):
    list_display = (
        "supplier",
        "store",
        "inventory_item",
        "status",
        "quantity_requested",
        "quantity_received",
        "ordered_at",
        "received_at",
    )
    list_filter = ("status", "store__region", "supplier")
    search_fields = ("supplier__name", "store__store_code", "inventory_item__sku")


@admin.register(RestockAlert)
class RestockAlertAdmin(admin.ModelAdmin):
    list_display = (
        "store",
        "inventory_item",
        "severity",
        "status",
        "triggered_by",
        "created_at",
    )
    list_filter = ("severity", "status", "store__region")
    search_fields = ("store__store_code", "inventory_item__sku")


@admin.register(SupplyUsageRecord)
class SupplyUsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        "store",
        "inventory_item",
        "usage_date",
        "quantity_used",
        "source_import_job",
    )
    list_filter = ("usage_date", "store__region")
    search_fields = ("store__store_code", "inventory_item__sku")


@admin.register(SupplySchedule)
class SupplyScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "store",
        "inventory_item",
        "recommended_source_type",
        "recommended_quantity",
        "status",
        "created_by_ai",
    )
    list_filter = ("status", "recommended_source_type", "created_by_ai")
    search_fields = ("store__store_code", "inventory_item__sku")
