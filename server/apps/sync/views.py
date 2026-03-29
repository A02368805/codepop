from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .models import SyncConflictLog, SyncOutboxEvent
from .services import retry_failed_outbox_events
from .tasks import process_pending_outbox_events_async


def _sync_context():
    queryset = SyncOutboxEvent.objects.order_by("-created_at")
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
        "events": queryset[:40],
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
        conflict = get_object_or_404(SyncConflictLog, pk=kwargs["conflict_id"])
        resolution_status = request.POST.get("resolution_status")

        if resolution_status:
            conflict.resolution_status = resolution_status
            conflict.save(update_fields=["resolution_status"])

        return HttpResponse('<div class="alert alert-info">Conflict Log</div>')
