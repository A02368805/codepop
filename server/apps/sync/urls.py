from django.urls import path

from .views import (
    NodeHealthView,
    SyncIngestView,
    SyncPanelView,
    SyncProcessPendingView,
    SyncResolveConflictView,
    SyncRetryFailedView,
    SyncWorkspaceView,
)

app_name = "sync"

urlpatterns = [
    path("", SyncWorkspaceView.as_view(), name="index"),
    path("panel/", SyncPanelView.as_view(), name="panel"),
    path("process/", SyncProcessPendingView.as_view(), name="process"),
    path("retry/", SyncRetryFailedView.as_view(), name="retry"),
    path(
        "conflicts/<uuid:conflict_id>/resolve/",
        SyncResolveConflictView.as_view(),
        name="resolve-conflict",
    ),
    path("ingest/", SyncIngestView.as_view(), name="ingest"),
    path("health/", NodeHealthView.as_view(), name="health"),
]
