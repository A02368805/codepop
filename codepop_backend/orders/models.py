from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Region(models.Model):
	name = models.CharField(max_length=100, unique=True)
	code = models.CharField(max_length=20, unique=True)

	def __str__(self):
		return f"{self.code} - {self.name}"


class Store(models.Model):
	name = models.CharField(max_length=100)
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="stores")

	class Meta:
		unique_together = ("name", "region")

	def __str__(self):
		return f"{self.name} ({self.region.code})"


class SupplyHub(models.Model):
	name = models.CharField(max_length=100)
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="hubs")

	class Meta:
		unique_together = ("name", "region")

	def __str__(self):
		return f"{self.name} ({self.region.code})"


class RegionAssignment(models.Model):
	ROLE_CHOICES = [
		("logistics_manager", "Logistics Manager"),
		("store_manager", "Store Manager"),
	]

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="region_assignments")
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="assignments")
	role = models.CharField(max_length=32, choices=ROLE_CHOICES)

	class Meta:
		unique_together = ("user", "region", "role")

	def __str__(self):
		return f"{self.user.username} - {self.role} - {self.region.code}"


class InventoryItem(models.Model):
	ITEM_TYPE_CHOICES = [
		("soda", "Soda"),
		("syrup", "Syrup"),
		("addin", "Add In"),
		("physical", "Physical"),
	]

	name = models.CharField(max_length=100)
	item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
	unit = models.CharField(max_length=20, default="units")

	class Meta:
		unique_together = ("name", "item_type")

	def __str__(self):
		return f"{self.name} ({self.item_type})"


class StoreInventoryBalance(models.Model):
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="inventory_balances")
	item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="store_balances")
	quantity = models.PositiveIntegerField(default=0)
	threshold = models.PositiveIntegerField(default=0)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("store", "item")

	def is_low(self):
		return self.quantity <= self.threshold

	def __str__(self):
		return f"{self.store.name}: {self.item.name}={self.quantity}"


class HubInventoryBalance(models.Model):
	hub = models.ForeignKey(SupplyHub, on_delete=models.CASCADE, related_name="inventory_balances")
	item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="hub_balances")
	quantity = models.PositiveIntegerField(default=0)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("hub", "item")

	def __str__(self):
		return f"{self.hub.name}: {self.item.name}={self.quantity}"


class RestockAlert(models.Model):
	STATUS_CHOICES = [
		("open", "Open"),
		("resolved", "Resolved"),
	]

	SEVERITY_CHOICES = [
		("low", "Low"),
		("critical", "Critical"),
	]

	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="restock_alerts")
	item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="restock_alerts")
	status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
	severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="low")
	message = models.CharField(max_length=255)
	created_at = models.DateTimeField(default=timezone.now)
	resolved_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-created_at"]

	def resolve(self):
		self.status = "resolved"
		self.resolved_at = timezone.now()
		self.save(update_fields=["status", "resolved_at"])

	def __str__(self):
		return f"{self.store.name} {self.item.name} {self.status}"


class SupplyTransfer(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("approved", "Approved"),
		("rejected", "Rejected"),
		("completed", "Completed"),
	]

	source_store = models.ForeignKey(
		Store,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="outbound_transfers",
	)
	source_hub = models.ForeignKey(
		SupplyHub,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="outbound_transfers",
	)
	destination_store = models.ForeignKey(
		Store,
		on_delete=models.CASCADE,
		related_name="inbound_transfers",
	)
	item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="transfers")
	quantity = models.PositiveIntegerField()
	status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
	requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_transfers")
	approved_by = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="approved_transfers",
	)
	created_at = models.DateTimeField(default=timezone.now)
	approved_at = models.DateTimeField(null=True, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)
	note = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ["-created_at"]

	def clean_source(self):
		return bool(self.source_store) ^ bool(self.source_hub)

	def __str__(self):
		return f"Transfer #{self.pk} {self.item.name} x{self.quantity} [{self.status}]"
