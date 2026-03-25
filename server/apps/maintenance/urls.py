from django.urls import path

from .views import (
    MaintenanceMachineAssignView,
    MaintenanceWorkspaceView,
    RepairAssignmentActionView,
)

app_name = "maintenance"

urlpatterns = [
    path("", MaintenanceWorkspaceView.as_view(), name="index"),
    path(
        "machines/<uuid:machine_id>/assign/",
        MaintenanceMachineAssignView.as_view(),
        name="machine-assign",
    ),
    path(
        "assignments/<uuid:assignment_id>/action/",
        RepairAssignmentActionView.as_view(),
        name="assignment-action",
    ),
]
