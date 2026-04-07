from django.urls import path

from .views import AnalyticsWorkspaceView, DashboardMetricsView

app_name = "analytics"

urlpatterns = [
    path("", AnalyticsWorkspaceView.as_view(), name="index"),
    path(
        "dashboard-metrics/", DashboardMetricsView.as_view(), name="dashboard-metrics"
    ),
]
