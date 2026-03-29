from django.urls import path

from .views import (
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationRegisterDeviceView,
    NotificationWorkspaceView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationWorkspaceView.as_view(), name="index"),
    path(
        "<uuid:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="mark-read",
    ),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path("register-device/", NotificationRegisterDeviceView.as_view(), name="register-device"),
]
