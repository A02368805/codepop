from django.urls import path

from .views import SyncPanelView, SyncProcessPendingView, SyncRetryFailedView, SyncWorkspaceView


app_name = "sync"

urlpatterns = [
    path("", SyncWorkspaceView.as_view(), name="index"),
    path("panel/", SyncPanelView.as_view(), name="panel"),
    path("process/", SyncProcessPendingView.as_view(), name="process"),
    path("retry/", SyncRetryFailedView.as_view(), name="retry"),
]
