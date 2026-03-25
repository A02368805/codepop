from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .models import SyncConflictLog, SyncOutboxEvent, SyncProjectionState
from .services import resolve_sync_conflict, retry_failed_outbox_events
from .tasks import process_pending_outbox_events_async


def _sync_context():
    queryset = SyncOutboxEvent.objects.order_by("-created_at")
    events = list(queryset[:40])
    return {
        "event_counts": {
            "pending": queryset.filter(status=SyncOutboxEvent.Status.PENDING).count(),
            "processing": queryset.filter(
                status=SyncOutboxEvent.Status.PROCESSING
            ).count(),
            "failed": queryset.filter(status=SyncOutboxEvent.Status.FAILED).count(),
            "dispatched": queryset.filter(
                status=SyncOutboxEvent.Status.DISPATCHED
            ).count(),
        },
        "event_rows": [
            {
                "event": event,
                "scope_display": (
                    event.source_scope.get("region_code")
                    or event.source_scope.get("store_id")
                    or "-"
                ),
            }
            for event in events
        ],
        "projection_counts": {
            "tracked": SyncProjectionState.objects.count(),
            "region": SyncProjectionState.objects.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.REGION
            ).count(),
            "store": SyncProjectionState.objects.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.STORE
            ).count(),
            "global": SyncProjectionState.objects.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.GLOBAL
            ).count(),
        },
        "projections": SyncProjectionState.objects.order_by("-updated_at")[:20],
        "conflict_counts": {
            "open": SyncConflictLog.objects.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.OPEN
            ).count(),
            "resolved": SyncConflictLog.objects.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.RESOLVED
            ).count(),
            "ignored": SyncConflictLog.objects.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.IGNORED
            ).count(),
        },
        "conflicts": SyncConflictLog.objects.order_by("-created_at")[:20],
        "resolution_open": SyncConflictLog.ResolutionStatus.OPEN,
        "resolution_resolved": SyncConflictLog.ResolutionStatus.RESOLVED,
        "resolution_ignored": SyncConflictLog.ResolutionStatus.IGNORED,
    }


def _render_sync_panel(request):
    html = render_to_string(
        "sync/partials/event_table.html", _sync_context(), request=request
    )
    return HttpResponse(html)


class SyncWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "sync/index.html"
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_sync_context())
        return context


class SyncPanelView(RoleRequiredMixin, TemplateView):
    template_name = "sync/partials/event_table.html"
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def get(self, request, *args, **kwargs):
        return _render_sync_panel(request)


class SyncProcessPendingView(RoleRequiredMixin, View):
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def post(self, request, *args, **kwargs):
        process_pending_outbox_events_async.delay(40)
        return _render_sync_panel(request)


class SyncRetryFailedView(RoleRequiredMixin, View):
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def post(self, request, *args, **kwargs):
        retry_failed_outbox_events(limit=40)
        return _render_sync_panel(request)


class SyncResolveConflictView(RoleRequiredMixin, View):
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def post(self, request, *args, **kwargs):
        conflict = SyncConflictLog.objects.get(pk=kwargs["conflict_id"])
        resolution = request.POST.get(
            "resolution_status",
            SyncConflictLog.ResolutionStatus.RESOLVED,
        )
        resolve_sync_conflict(conflict, resolution_status=resolution)
        return _render_sync_panel(request)
