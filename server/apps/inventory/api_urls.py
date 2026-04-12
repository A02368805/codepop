from django.urls import path

from .api_views import BackendInventoryMutationView, BackendInventoryReportView

app_name = "inventory_api"

urlpatterns = [
    path("report/", BackendInventoryReportView.as_view(), name="report"),
    path("<uuid:balance_id>/", BackendInventoryMutationView.as_view(), name="update"),
]
