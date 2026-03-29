import uuid

from django.db import models


class Notification(models.Model):
    class Category(models.TextChoices):
        INFO = "info", "Info"
        ALERT = "alert", "Alert"
        TASK = "task", "Task"

    class DeliveryChannel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        PUSH = "push", "Push"
        EMAIL = "email", "Email"

    class NotificationType(models.TextChoices):
        GENERIC = "generic", "Generic"
        IMPORT_RESULT = "import_result", "Import Result"
        MACHINE_ALERT = "machine_alert", "Machine Alert"
        ORDER_UPDATE = "order_update", "Order Update"
        REPAIR_ASSIGNMENT = "repair_assignment", "Repair Assignment"
        TRANSFER_UPDATE = "transfer_update", "Transfer Update"

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="notifications", on_delete=models.CASCADE
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.GENERIC,
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    payload_json = models.JSONField(default=dict, blank=True)
    delivery_channel = models.CharField(
        max_length=16,
        choices=DeliveryChannel.choices,
        default=DeliveryChannel.IN_APP,
    )
    delivery_status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.INFO
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("is_read", "-created_at")
        indexes = [
            models.Index(fields=("user", "is_read", "-created_at")),
            models.Index(fields=("notification_type", "delivery_status")),
        ]

    def __str__(self):
        return self.title


class DeviceRegistration(models.Model):
    class Platform(models.TextChoices):
        WEB = "web", "Web"
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    class PushProvider(models.TextChoices):
        WEB_PUSH = "web_push", "Web Push"
        FCM = "fcm", "FCM"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        related_name="notification_devices",
        on_delete=models.CASCADE,
    )
    device_token = models.CharField(max_length=255, unique=True)
    device_label = models.CharField(max_length=120, blank=True)
    platform = models.CharField(
        max_length=16, choices=Platform.choices, default=Platform.WEB
    )
    push_provider = models.CharField(
        max_length=16, choices=PushProvider.choices, default=PushProvider.WEB_PUSH
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen_at",)
        indexes = [
            models.Index(fields=("user", "is_active", "-last_seen_at")),
        ]

    def __str__(self):
        return f"{self.user.email} / {self.device_token[:20]}"
