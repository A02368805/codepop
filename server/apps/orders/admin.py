from django.contrib import admin

from .models import GuestOrderContact, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "public_order_code",
        "store",
        "customer",
        "order_type",
        "status",
        "total_amount",
    )
    list_filter = ("status", "order_type", "store")
    search_fields = (
        "public_order_code",
        "customer__email",
        "store__name",
        "store__store_code",
    )
    inlines = [OrderItemInline]


@admin.register(GuestOrderContact)
class GuestOrderContactAdmin(admin.ModelAdmin):
    list_display = ("lookup_code", "display_name", "email", "order")
