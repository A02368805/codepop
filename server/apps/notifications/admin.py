from django.contrib import admin

from .models import DeviceRegistration, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "notification_type",
        "category",
        "delivery_status",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "category", "delivery_status", "is_read")
    search_fields = ("title", "message", "user__email")


@admin.register(DeviceRegistration)
class DeviceRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "platform",
        "push_provider",
        "is_active",
        "last_seen_at",
    )
    list_filter = ("platform", "push_provider", "is_active")
    search_fields = ("user__email", "device_label", "device_token")
