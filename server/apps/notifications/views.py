from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .models import DeviceRegistration, Notification
from .services import register_device


def _notification_context(request):
    state_filter = (
        request.GET.get("state", "").strip()
        or request.POST.get("state", "").strip()
        or "all"
    )
    notifications = request.user.notifications.order_by("is_read", "-created_at")
    if state_filter == "unread":
        notifications = notifications.filter(is_read=False)
    return {
        "notifications": notifications,
        "state_filter": state_filter,
        "unread_count": request.user.notifications.filter(is_read=False).count(),
    }


def _render_workspace_response(request):
    html = render_to_string(
        "notifications/partials/workspace.html",
        _notification_context(request),
        request=request,
    )
    return HttpResponse(html)


def _workspace_redirect(request):
    state_filter = request.POST.get("state", "").strip()
    url = reverse("notifications:index")
    if state_filter:
        url = f"{url}?state={state_filter}"
    return redirect(url)


class NotificationWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "notifications/index.html"
    allowed_roles = tuple(choice for choice, _ in User.Role.choices)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_notification_context(self.request))
        return context

    def get(self, request, *args, **kwargs):
        if getattr(request, "htmx", False):
            return _render_workspace_response(request)
        return super().get(request, *args, **kwargs)


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, pk=kwargs["notification_id"], user=request.user
        )
        notification.is_read = True
        notification.read_at = notification.read_at or timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
        if not getattr(request, "htmx", False):
            return _workspace_redirect(request)
        return _render_workspace_response(request)


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        request.user.notifications.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
            updated_at=timezone.now(),
        )
        if not getattr(request, "htmx", False):
            return _workspace_redirect(request)
        return _render_workspace_response(request)


class NotificationDeviceRegistrationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        device_token = request.POST.get("device_token", "").strip()
        if not device_token:
            return JsonResponse(
                {"registered": False, "error": "device_token is required."},
                status=400,
            )
        device = register_device(
            user=request.user,
            device_token=device_token,
            platform=request.POST.get("platform", "").strip()
            or DeviceRegistration.Platform.WEB,
            push_provider=request.POST.get("push_provider", "").strip()
            or DeviceRegistration.PushProvider.WEB_PUSH,
            device_label=request.POST.get("device_label", "").strip(),
        )
        return JsonResponse(
            {
                "registered": True,
                "device_id": str(device.pk),
                "platform": device.platform,
                "push_provider": device.push_provider,
            }
        )
