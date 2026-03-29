import uuid

from django.db import models


class SyncOutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DISPATCHED = "dispatched", "Dispatched"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=120)
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.CharField(max_length=80)
    entity_version = models.PositiveIntegerField(default=1)
    source_scope = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING
    )
    payload = models.JSONField(default=dict, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "next_attempt_at"))]

    def __str__(self):
        return self.event_type


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        "users.User",
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    store = models.ForeignKey(
        "stores.Store",
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    region = models.ForeignKey(
        "stores.Region",
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.action} / {self.entity_type} / {self.entity_id}"


class SyncProjectionState(models.Model):
    class ReceiverScope(models.TextChoices):
        REGION = "region", "Region"
        STORE = "store", "Store"
        GLOBAL = "global", "Global"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receiver_scope_type = models.CharField(max_length=24, choices=ReceiverScope.choices)
    receiver_scope_key = models.CharField(max_length=80)
    receiver_label = models.CharField(max_length=160)
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.CharField(max_length=80)
    last_event_type = models.CharField(max_length=120)
    last_entity_version = models.PositiveIntegerField(default=0)
    source_scope = models.JSONField(default=dict, blank=True)
    payload_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(
                fields=["receiver_scope_type", "receiver_scope_key"],
            ),
            models.Index(
                fields=["aggregate_type", "aggregate_id"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "receiver_scope_type",
                    "receiver_scope_key",
                    "aggregate_type",
                    "aggregate_id",
                ],
                name="unique_sync_projection_receiver_entity",
            )
        ]

    def __str__(self):
        return f"{self.aggregate_type} / {self.aggregate_id}"


class SyncConflictLog(models.Model):
    class ReceiverScope(models.TextChoices):
        REGION = "region", "Region"
        STORE = "store", "Store"
        GLOBAL = "global", "Global"

    class ConflictType(models.TextChoices):
        STALE_EVENT = "stale_event", "Stale Event"
        INVALID_SCOPE = "invalid_scope", "Invalid Scope"
        OWNERSHIP_MISMATCH = "ownership_mismatch", "Ownership Mismatch"
        INVALID_TRANSITION = "invalid_transition", "Invalid Transition"

    class ResolutionStatus(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receiver_scope_type = models.CharField(max_length=24, choices=ReceiverScope.choices)
    receiver_scope_key = models.CharField(max_length=80)
    receiver_label = models.CharField(max_length=160)
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.CharField(max_length=80)
    conflict_type = models.CharField(max_length=32, choices=ConflictType.choices)
    resolution_status = models.CharField(
        max_length=16,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.OPEN,
    )
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    outbox_event = models.ForeignKey(
        "sync.SyncOutboxEvent",
        related_name="conflicts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["resolution_status", "conflict_type"],
            ),
            models.Index(
                fields=["aggregate_type", "aggregate_id"],
            ),
        ]

    def __str__(self):
        return f"{self.conflict_type} / {self.aggregate_type} / {self.aggregate_id}"
