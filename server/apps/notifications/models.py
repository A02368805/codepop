import uuid

from django.db import models


class Notification(models.Model):
    class Category(models.TextChoices):
        INFO = "info", "Info"
        ALERT = "alert", "Alert"
        TASK = "task", "Task"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="notifications", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title
