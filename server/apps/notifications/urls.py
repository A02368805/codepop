from django.urls import path

from .views import (
    NotificationDeviceRegistrationView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationWorkspaceView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationWorkspaceView.as_view(), name="index"),
    path(
        "register-device/",
        NotificationDeviceRegistrationView.as_view(),
        name="register-device",
    ),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path(
        "<uuid:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="mark-read",
    ),
]
