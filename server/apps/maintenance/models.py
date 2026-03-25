import uuid
from decimal import Decimal

from django.db import models


class MachineType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    default_service_interval_days = models.PositiveIntegerField()
    warning_max_operational_days = models.PositiveIntegerField()
    error_max_days = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.code


class Machine(models.Model):
    class Status(models.TextChoices):
        NORMAL = "normal", "Normal"
        REPAIR_START = "repair-start", "Repair Start"
        REPAIR_END = "repair-end", "Repair End"
        SCHEDULE_SERVICE = "schedule-service", "Schedule Service"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        OUT_OF_ORDER = "out-of-order", "Out of Order"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    machine_uid = models.CharField(max_length=80, unique=True)
    store = models.ForeignKey(
        "stores.Store", related_name="machines", on_delete=models.CASCADE
    )
    machine_type = models.ForeignKey(
        "maintenance.MachineType", related_name="machines", on_delete=models.PROTECT
    )
    display_name = models.CharField(max_length=160)
    operational_from_date = models.DateField()
    current_status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.NORMAL
    )
    current_status_date = models.DateField(null=True, blank=True)
    last_service_date = models.DateField(null=True, blank=True)
    next_service_due_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("store__store_code", "machine_uid")
        indexes = [models.Index(fields=("store", "current_status"))]

    def __str__(self):
        return self.display_name


class MachineStatusEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    machine = models.ForeignKey(
        "maintenance.Machine", related_name="status_events", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=24, choices=Machine.Status.choices)
    status_date = models.DateField()
    source_import_job = models.ForeignKey(
        "imports.ImportJob",
        related_name="machine_status_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-status_date", "-created_at")
        indexes = [models.Index(fields=("machine", "-status_date"))]

    def __str__(self):
        return f"{self.machine.machine_uid} / {self.status} / {self.status_date}"


class RepairAssignment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assigned_to = models.ForeignKey(
        "users.User", related_name="repair_assignments", on_delete=models.PROTECT
    )
    machine = models.ForeignKey(
        "maintenance.Machine",
        related_name="repair_assignments",
        on_delete=models.CASCADE,
    )
    store = models.ForeignKey(
        "stores.Store", related_name="repair_assignments", on_delete=models.PROTECT
    )
    priority_score = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.SCHEDULED
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by_system = models.BooleanField(default=True)
    route_batch_key = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("scheduled_for", "-priority_score")
        indexes = [models.Index(fields=("assigned_to", "status", "scheduled_for"))]

    def __str__(self):
        return f"{self.machine.machine_uid} / {self.status}"


class MaintenancePolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    machine_type = models.ForeignKey(
        "maintenance.MachineType", related_name="policies", on_delete=models.CASCADE
    )
    region = models.ForeignKey(
        "stores.Region",
        related_name="maintenance_policies",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    max_days_between_service = models.PositiveIntegerField()
    warning_shutdown_days = models.PositiveIntegerField()
    schedule_service_window_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("machine_type__code", "region__code")

    def __str__(self):
        if self.region_id:
            return f"{self.machine_type.code} / {self.region.code}"
        return f"{self.machine_type.code} / default"
