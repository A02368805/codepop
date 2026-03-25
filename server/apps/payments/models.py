import uuid
from decimal import Decimal

from django.db import models


class PaymentTransaction(models.Model):
    class Provider(models.TextChoices):
        MOCK = "mock", "Mock"
        STRIPE = "stripe", "Stripe"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order", related_name="payment_transaction", on_delete=models.CASCADE
    )
    store = models.ForeignKey(
        "stores.Store", related_name="payment_transactions", on_delete=models.PROTECT
    )
    provider = models.CharField(
        max_length=24, choices=Provider.choices, default=Provider.STRIPE
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING
    )
    amount_authorized = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    amount_captured = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    amount_refunded = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    checkout_session_id = models.CharField(max_length=120, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=120, blank=True)
    failure_reason = models.TextField(blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.order.public_order_code} [{self.status}]"


class RevenueLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        SALE = "sale", "Sale"
        REFUND = "refund", "Refund"
        ADJUSTMENT = "adjustment", "Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "stores.Store", related_name="revenue_entries", on_delete=models.PROTECT
    )
    order = models.ForeignKey(
        "orders.Order",
        related_name="revenue_entries",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    entry_type = models.CharField(max_length=16, choices=EntryType.choices)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    posted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-posted_at",)

    def __str__(self):
        return f"{self.store.store_code} / {self.entry_type} / {self.net_amount}"


class PaymentWebhookEvent(models.Model):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=24, choices=Provider.choices)
    provider_event_id = models.CharField(max_length=160, unique=True)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-processed_at",)

    def __str__(self):
        return f"{self.provider} / {self.provider_event_id}"
