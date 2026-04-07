from django.contrib import admin

from .models import PaymentTransaction, RevenueLedgerEntry


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "store",
        "provider",
        "status",
        "amount_authorized",
        "amount_captured",
        "amount_refunded",
    )
    list_filter = ("provider", "status", "store")
    search_fields = ("order__public_order_code", "stripe_payment_intent_id")


@admin.register(RevenueLedgerEntry)
class RevenueLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("store", "entry_type", "gross_amount", "net_amount", "posted_at")
    list_filter = ("entry_type", "store")
    search_fields = ("store__store_code", "order__public_order_code")
