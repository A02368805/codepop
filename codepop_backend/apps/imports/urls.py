from django.urls import path

from .views import (
    ImportHistoryView,
    ImportWorkspaceView,
    RepairStatusImportView,
    SupplyUsageImportView,
)


app_name = "imports"

urlpatterns = [
    path("", ImportWorkspaceView.as_view(), name="index"),
    path("history/", ImportHistoryView.as_view(), name="history"),
    path("supply-usage/", SupplyUsageImportView.as_view(), name="supply-usage"),
    path("repair-status/", RepairStatusImportView.as_view(), name="repair-status"),
]
