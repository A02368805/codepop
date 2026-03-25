from django.contrib import admin

from .models import (
    HubInventoryBalance,
    SupplyHub,
    SupplyTransfer,
    SupplyTransferLineItem,
)


class SupplyTransferLineItemInline(admin.TabularInline):
    model = SupplyTransferLineItem
    extra = 0


@admin.register(SupplyHub)
class SupplyHubAdmin(admin.ModelAdmin):
    list_display = ("hub_code", "name", "region", "city", "state_code", "is_active")
    list_filter = ("region", "state_code", "is_active")
    search_fields = ("name", "hub_code")


@admin.register(HubInventoryBalance)
class HubInventoryBalanceAdmin(admin.ModelAdmin):
    list_display = ("hub", "inventory_item", "on_hand_quantity", "reserved_quantity")
    list_filter = ("hub__region", "hub")
    search_fields = ("hub__hub_code", "inventory_item__sku", "inventory_item__name")


@admin.register(SupplyTransfer)
class SupplyTransferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_type",
        "source_store",
        "source_hub",
        "destination_store",
        "status",
        "transfer_scope",
        "distance_miles",
    )
    list_filter = ("status", "transfer_scope", "source_type")
    search_fields = (
        "destination_store__store_code",
        "source_store__store_code",
        "source_hub__hub_code",
    )
    inlines = [SupplyTransferLineItemInline]
