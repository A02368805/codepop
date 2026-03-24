import uuid
from decimal import Decimal

from django.db import models
from django.db.models import F, Q


class SupplyHub(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        "stores.Region", related_name="supply_hubs", on_delete=models.PROTECT
    )
    hub_code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=140)
    city = models.CharField(max_length=80)
    state_code = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("region__code", "hub_code")

    def __str__(self):
        return self.name


class HubInventoryBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hub = models.ForeignKey(
        "supply_hubs.SupplyHub",
        related_name="inventory_balances",
        on_delete=models.CASCADE,
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem", related_name="hub_balances", on_delete=models.CASCADE
    )
    on_hand_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    reserved_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("hub__hub_code", "inventory_item__sku")
        constraints = [
            models.UniqueConstraint(
                fields=("hub", "inventory_item"),
                name="unique_hub_inventory_balance",
            ),
            models.CheckConstraint(
                check=Q(on_hand_quantity__gte=0) & Q(reserved_quantity__gte=0),
                name="hub_inventory_quantities_non_negative",
            ),
            models.CheckConstraint(
                check=Q(on_hand_quantity__gte=F("reserved_quantity")),
                name="hub_inventory_reserved_not_greater_than_on_hand",
            ),
        ]

    def __str__(self):
        return f"{self.hub.hub_code} / {self.inventory_item.sku}"


class SupplyTransfer(models.Model):
    class SourceType(models.TextChoices):
        STORE = "store", "Store"
        HUB = "hub", "Hub"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        RESERVED = "reserved", "Reserved"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        RECEIVED = "received", "Received"
        REJECTED = "rejected", "Rejected"
        CANCELED = "canceled", "Canceled"

    class TransferScope(models.TextChoices):
        SAME_REGION_STORE = "same_region_store", "Same-Region Store"
        HUB_TO_STORE = "hub_to_store", "Hub To Store"
        CROSS_REGION_HUB = "cross_region_hub", "Cross-Region Hub"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    source_store = models.ForeignKey(
        "stores.Store",
        related_name="outbound_transfers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    source_hub = models.ForeignKey(
        "supply_hubs.SupplyHub",
        related_name="outbound_transfers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    destination_store = models.ForeignKey(
        "stores.Store", related_name="inbound_transfers", on_delete=models.PROTECT
    )
    requested_by = models.ForeignKey(
        "users.User", related_name="requested_transfers", on_delete=models.PROTECT
    )
    approved_by = models.ForeignKey(
        "users.User",
        related_name="approved_transfers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.REQUESTED
    )
    transfer_scope = models.CharField(max_length=24, choices=TransferScope.choices)
    distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    is_ai_draft = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-requested_at",)
        indexes = [
            models.Index(fields=("status", "requested_at")),
            models.Index(fields=("destination_store", "status")),
        ]

    def __str__(self):
        return f"{self.id} [{self.status}]"

    @property
    def destination_region(self):
        return self.destination_store.region


class SupplyTransferLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(
        "supply_hubs.SupplyTransfer",
        related_name="line_items",
        on_delete=models.CASCADE,
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        related_name="transfer_line_items",
        on_delete=models.PROTECT,
    )
    quantity_requested = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_approved = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        ordering = ("inventory_item__sku",)

    def __str__(self):
        return f"{self.transfer_id} / {self.inventory_item.sku}"
