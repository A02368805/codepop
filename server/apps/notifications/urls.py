from django.urls import path

from .views import NotificationMarkReadView, NotificationWorkspaceView


app_name = "notifications"

urlpatterns = [
    path("", NotificationWorkspaceView.as_view(), name="index"),
    path("<uuid:notification_id>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
]
