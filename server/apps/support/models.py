import uuid

from django.db import models


class SupportConversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        related_name="support_conversations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    guest_session_key = models.CharField(max_length=64, blank=True, db_index=True)
    linked_order = models.ForeignKey(
        "orders.Order",
        related_name="support_conversations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    linked_store = models.ForeignKey(
        "stores.Store",
        related_name="support_conversations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    last_intent = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("status", "updated_at")),
            models.Index(fields=("user", "updated_at")),
        ]

    def __str__(self):
        owner = (
            self.user.email if self.user_id else f"guest:{self.guest_session_key[:8]}"
        )
        return f"SupportConversation<{owner}>"


class SupportMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "support.SupportConversation",
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    intent = models.CharField(max_length=64, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class SupportEscalation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "support.SupportConversation",
        related_name="escalations",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "users.User",
        related_name="support_escalations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    linked_order = models.ForeignKey(
        "orders.Order",
        related_name="support_escalations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    linked_store = models.ForeignKey(
        "stores.Store",
        related_name="support_escalations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    contact_email = models.EmailField(blank=True)
    summary = models.TextField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"SupportEscalation<{self.status}>"
