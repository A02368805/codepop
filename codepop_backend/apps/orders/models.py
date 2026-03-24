import uuid
from decimal import Decimal

from django.db import models


class Order(models.Model):
    class OrderType(models.TextChoices):
        ACCOUNT = "account", "Account"
        GUEST = "guest", "Guest"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PRICING_VALIDATED = "pricing_validated", "Pricing Validated"
        PAYMENT_PENDING = "payment_pending", "Payment Pending"
        PAID = "paid", "Paid"
        QUEUED = "queued", "Queued"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        PICKED_UP = "picked_up", "Picked Up"
        REFUND_PENDING = "refund_pending", "Refund Pending"
        REFUNDED = "refunded", "Refunded"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    class RefundStatus(models.TextChoices):
        NONE = "none", "None"
        REQUESTED = "requested", "Requested"
        REFUNDED = "refunded", "Refunded"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_order_code = models.CharField(max_length=32, unique=True)
    store = models.ForeignKey(
        "stores.Store", related_name="orders", on_delete=models.PROTECT
    )
    customer = models.ForeignKey(
        "users.User",
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    order_type = models.CharField(
        max_length=16, choices=OrderType.choices, default=OrderType.ACCOUNT
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    pickup_time_requested = models.DateTimeField(null=True, blank=True)
    pickup_time_estimated = models.DateTimeField(null=True, blank=True)
    subtotal_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")
    placed_at = models.DateTimeField(null=True, blank=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    locker_number = models.CharField(max_length=12, blank=True)
    locker_code = models.CharField(max_length=16, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)
    refund_status = models.CharField(
        max_length=16, choices=RefundStatus.choices, default=RefundStatus.NONE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("store", "status")),
            models.Index(fields=("customer", "placed_at")),
        ]

    def __str__(self):
        return f"{self.public_order_code} ({self.status})"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order", related_name="items", on_delete=models.CASCADE
    )
    template_reference_id = models.UUIDField(null=True, blank=True)
    display_name_snapshot = models.CharField(max_length=160)
    size_snapshot = models.CharField(max_length=24)
    base_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    customizations_json = models.JSONField(default=dict, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ("display_name_snapshot",)

    def __str__(self):
        return f"{self.quantity}x {self.display_name_snapshot}"


class GuestOrderContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order", related_name="guest_contact", on_delete=models.CASCADE
    )
    display_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    lookup_code = models.CharField(max_length=24, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.lookup_code
