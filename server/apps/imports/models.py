import uuid

from django.db import models


class ImportJob(models.Model):
    class ImportType(models.TextChoices):
        SUPPLY_USAGE = "supply_usage", "Supply Usage"
        REPAIR_STATUS = "repair_status", "Repair Status"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        "users.User",
        related_name="import_jobs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    import_type = models.CharField(max_length=32, choices=ImportType.choices)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING
    )
    original_filename = models.CharField(max_length=255)
    row_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_report_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("import_type", "status", "-created_at"))]

    def __str__(self):
        return f"{self.import_type} ({self.status})"
