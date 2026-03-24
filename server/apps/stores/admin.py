from django.contrib import admin

from .models import Region, Store


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "hub_city", "hub_state_code", "created_at")
    search_fields = ("name", "code", "hub_city")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("store_code", "name", "region", "city", "state_code", "is_active")
    list_filter = ("region", "state_code", "is_active")
    search_fields = ("name", "slug", "city", "store_code")
