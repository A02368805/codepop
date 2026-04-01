from django.contrib import admin

from .models import SupportConversation, SupportEscalation, SupportMessage


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ("role", "intent", "created_at", "content")
    can_delete = False


@admin.register(SupportConversation)
class SupportConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "guest_session_key",
        "status",
        "linked_order",
        "linked_store",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "guest_session_key", "linked_order__public_order_code")
    inlines = [SupportMessageInline]


@admin.register(SupportEscalation)
class SupportEscalationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "user",
        "contact_email",
        "linked_order",
        "linked_store",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("contact_email", "summary", "linked_order__public_order_code")
