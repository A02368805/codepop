import uuid
from decimal import Decimal

from django.db import models
from django.db.models import F, Q


class InventoryItem(models.Model):
    class Category(models.TextChoices):
        SODA = "soda", "Soda"
        SYRUP = "syrup", "Syrup"
        ADD_IN = "add_in", "Add-In"
        DAIRY = "dairy", "Dairy"
        CUPS = "cups", "Cups"
        LIDS = "lids", "Lids"
        ICE_CREAM = "ice_cream", "Ice Cream"
        CLEANING = "cleaning", "Cleaning"
        EQUIPMENT = "equipment", "Equipment"
        PACKAGING = "packaging", "Packaging"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=24, choices=Category.choices)
    unit_of_measure = models.CharField(max_length=32, default="unit")
    is_perishable = models.BooleanField(default=False)
    requires_frozen_storage = models.BooleanField(default=False)
    default_low_stock_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sku",)

    def __str__(self):
        return f"{self.sku} - {self.name}"


class StoreInventoryBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "stores.Store", related_name="inventory_balances", on_delete=models.CASCADE
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="store_balances",
        on_delete=models.CASCADE,
    )
    on_hand_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    reserved_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    reorder_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("store__store_code", "inventory_item__sku")
        constraints = [
            models.UniqueConstraint(
                fields=("store", "inventory_item"),
                name="unique_store_inventory_balance",
            ),
            models.CheckConstraint(
                check=Q(on_hand_quantity__gte=0) & Q(reserved_quantity__gte=0),
                name="store_inventory_quantities_non_negative",
            ),
            models.CheckConstraint(
                check=Q(on_hand_quantity__gte=F("reserved_quantity")),
                name="store_inventory_reserved_not_greater_than_on_hand",
            ),
        ]

    def __str__(self):
        return f"{self.store.store_code} / {self.inventory_item.sku}"


class LocalSupplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    service_region = models.ForeignKey(
        "stores.Region",
        related_name="local_suppliers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    item_categories_json = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class SupplierReplenishment(models.Model):
    class Status(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        RECEIVED = "received", "Received"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "inventory.LocalSupplier",
        related_name="replenishments",
        on_delete=models.PROTECT,
    )
    store = models.ForeignKey(
        "stores.Store", related_name="supplier_replenishments", on_delete=models.PROTECT
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="supplier_replenishments",
        on_delete=models.PROTECT,
    )
    quantity_requested = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    requested_by = models.ForeignKey(
        "users.User",
        related_name="requested_replenishments",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    ordered_at = models.DateTimeField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        "users.User",
        related_name="recorded_replenishments",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RECEIVED
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-ordered_at", "-received_at")
        constraints = [
            models.CheckConstraint(
                check=Q(quantity_requested__gte=0) & Q(quantity_received__gte=0),
                name="supplier_replenishment_quantities_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.supplier.name} -> {self.store.store_code} ({self.status})"


class RestockAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "stores.Store", related_name="restock_alerts", on_delete=models.CASCADE
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="restock_alerts",
        on_delete=models.CASCADE,
    )
    severity = models.CharField(max_length=16, choices=Severity.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    triggered_by = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.store.store_code} / {self.inventory_item.sku} / {self.severity}"


class SupplyUsageRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "stores.Store", related_name="supply_usage_records", on_delete=models.CASCADE
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="supply_usage_records",
        on_delete=models.CASCADE,
    )
    usage_date = models.DateField()
    quantity_used = models.DecimalField(max_digits=12, decimal_places=2)
    source_import_job = models.ForeignKey(
        "imports.ImportJob",
        related_name="supply_usage_records",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-usage_date", "store__store_code")

    def __str__(self):
        return (
            f"{self.store.store_code} / {self.inventory_item.sku} / {self.usage_date}"
        )


class SupplySchedule(models.Model):
    class RecommendedSourceType(models.TextChoices):
        HUB = "hub", "Hub"
        LOCAL_SUPPLIER = "local_supplier", "Local Supplier"
        LOCAL_STORE = "local_store", "Local Store"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "stores.Store", related_name="supply_schedules", on_delete=models.CASCADE
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="supply_schedules",
        on_delete=models.CASCADE,
    )
    recommended_source_type = models.CharField(
        max_length=24, choices=RecommendedSourceType.choices
    )
    recommended_source_reference = models.JSONField(default=dict, blank=True)
    recommended_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    recommended_frequency_days = models.PositiveIntegerField()
    created_by_ai = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        "users.User",
        related_name="approved_supply_schedules",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("store__store_code", "inventory_item__sku")

    def __str__(self):
        return f"{self.store.store_code} / {self.inventory_item.sku} / {self.status}"
