import json
import logging

from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .models import SyncConflictLog, SyncOutboxEvent, SyncProjectionState
from .services import (
    ingest_event_from_peer,
    resolve_sync_conflict,
    retry_failed_outbox_events,
)
from .tasks import process_pending_outbox_events_async

health_logger = logging.getLogger("distributed.health")


def _sync_context():
    queryset = SyncOutboxEvent.objects.order_by("-created_at")
    conflict_queryset = SyncConflictLog.objects.order_by("-created_at")
    projection_queryset = SyncProjectionState.objects.order_by("-updated_at")
    events = list(queryset[:40])
    for event in events:
        source_scope = event.source_scope or {}
        event.scope_label = (
            source_scope.get("region_code") or source_scope.get("store_id") or "-"
        )
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
        "events": events,
        "conflict_counts": {
            "open": conflict_queryset.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.OPEN
            ).count(),
            "resolved": conflict_queryset.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.RESOLVED
            ).count(),
            "ignored": conflict_queryset.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.IGNORED
            ).count(),
        },
        "open_conflicts": conflict_queryset.filter(
            resolution_status=SyncConflictLog.ResolutionStatus.OPEN
        )[:20],
        "recent_conflicts": conflict_queryset[:20],
        "projection_counts": {
            "region": projection_queryset.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.REGION
            ).count(),
            "store": projection_queryset.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.STORE
            ).count(),
            "global": projection_queryset.filter(
                receiver_scope_type=SyncProjectionState.ReceiverScope.GLOBAL
            ).count(),
        },
        "projections": projection_queryset[:25],
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
        resolution_status = (
            request.POST.get("resolution_status")
            or SyncConflictLog.ResolutionStatus.RESOLVED
        )

        if resolution_status in {
            SyncConflictLog.ResolutionStatus.RESOLVED,
            SyncConflictLog.ResolutionStatus.IGNORED,
        }:
            resolve_sync_conflict(
                conflict,
                resolution_status=resolution_status,
            )

        return _render_sync_panel(request)


@method_decorator(csrf_exempt, name="dispatch")
class NodeHealthView(View):
    """
    Health check endpoint for distributed node monitoring.
    Returns this node's identity, status, and peer connectivity.
    Authenticates via X-Sync-Token for peer info, or returns basic status without auth.
    """

    def get(self, request, *args, **kwargs):
        import requests as http_requests
        from django.conf import settings

        node_id = settings.STORE_ID or "unconfigured"
        sync_enabled = settings.SYNC_PUSH_ENABLED
        is_probe_request = request.headers.get("X-Distributed-Health-Probe", "") == "1"
        authenticated = (
            request.headers.get("X-Sync-Token", "") == settings.SYNC_API_SECRET
            and settings.SYNC_API_SECRET
        )

        health = {
            "status": "ok",
            "node_id": node_id,
            "sync_enabled": sync_enabled,
        }

        # Probe requests are for liveness only and must not recurse into peers.
        if is_probe_request:
            return JsonResponse(health)

        # Only expose peer details to authenticated callers.
        if authenticated and settings.PEER_STORES:
            peers = {}
            for peer_id, peer_url in settings.PEER_STORES.items():
                try:
                    health_logger.info(
                        "DISTRIBUTED: Health check reaching peer '%s' at %s.",
                        peer_id,
                        peer_url,
                    )
                    resp = http_requests.get(
                        f"{peer_url}/sync/health/",
                        headers={
                            "X-Sync-Token": settings.SYNC_API_SECRET,
                            "X-Distributed-Health-Probe": "1",
                        },
                        timeout=3,
                    )
                    peers[peer_id] = {
                        "url": peer_url,
                        "reachable": resp.status_code == 200,
                    }
                except Exception as exc:
                    health_logger.warning(
                        "DISTRIBUTED: Health check could not reach peer '%s' at %s: %s",
                        peer_id,
                        peer_url,
                        exc,
                    )
                    peers[peer_id] = {"url": peer_url, "reachable": False}
            health["peers"] = peers

        return JsonResponse(health)


@method_decorator(csrf_exempt, name="dispatch")
class SyncIngestView(View):
    """
    Machine-to-machine endpoint for receiving sync events from peer stores.
    Authenticates via X-Sync-Token header (must match SYNC_API_SECRET).
    """

    def post(self, request, *args, **kwargs):
        from django.conf import settings

        # Authenticate via shared secret
        token = request.headers.get("X-Sync-Token", "")
        if not token or token != settings.SYNC_API_SECRET:
            return JsonResponse({"error": "unauthorized"}, status=401)

        # Get origin node ID
        origin_node_id = request.headers.get("X-Origin-Node", "")
        if not origin_node_id:
            return JsonResponse({"error": "missing origin"}, status=400)

        # Parse payload
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "invalid json"}, status=400)

        try:
            event = ingest_event_from_peer(payload, origin_node_id=origin_node_id)
            return JsonResponse({"status": "ok", "event_id": str(event.pk)})
        except Exception as exc:
            return JsonResponse(
                {"error": "processing failed", "detail": str(exc)},
                status=400,
            )
