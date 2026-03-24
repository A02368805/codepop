from django.urls import path

from .views import MaintenanceWorkspaceView


app_name = "maintenance"

urlpatterns = [
    path("", MaintenanceWorkspaceView.as_view(), name="index"),
]
