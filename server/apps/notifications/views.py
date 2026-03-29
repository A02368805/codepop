from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .models import DeviceRegistration, Notification


class NotificationWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "notifications/index.html"
    allowed_roles = tuple(choice for choice, _ in User.Role.choices)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications = self.request.user.notifications.order_by("-created_at")

        # Filter by state parameter
        state = self.request.GET.get("state", "all")
        if state == "unread":
            notifications = notifications.filter(is_read=False)
        elif state == "read":
            notifications = notifications.filter(is_read=True)

        context["notifications"] = notifications
        context["state"] = state
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, pk=kwargs["notification_id"], user=request.user
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])

        notifications = request.user.notifications.order_by("-created_at")

        # Filter by state parameter
        state = request.POST.get("state", "all")
        if state == "unread":
            notifications = notifications.filter(is_read=False)
        elif state == "read":
            notifications = notifications.filter(is_read=True)

        html = render_to_string(
            "notifications/partials/list.html",
            {"notifications": notifications},
            request=request,
        )
        return HttpResponse(html)


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        request.user.notifications.filter(is_read=False).update(is_read=True)

        notifications = request.user.notifications.order_by("-created_at")

        # Filter by state parameter
        state = request.POST.get("state", "all")
        if state == "unread":
            notifications = notifications.filter(is_read=False)
        elif state == "read":
            notifications = notifications.filter(is_read=True)

        html = render_to_string(
            "notifications/partials/list.html",
            {"notifications": notifications},
            request=request,
        )
        return HttpResponse(html)


class NotificationRegisterDeviceView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        device_token = request.POST.get("device_token")
        platform = request.POST.get("platform", DeviceRegistration.Platform.WEB)
        push_provider = request.POST.get("push_provider", DeviceRegistration.PushProvider.WEB_PUSH)
        device_label = request.POST.get("device_label", "")

        DeviceRegistration.objects.update_or_create(
            user=request.user,
            device_token=device_token,
            defaults={
                "platform": platform,
                "push_provider": push_provider,
                "device_label": device_label,
                "is_active": True,
            },
        )
        return HttpResponse(status=200)
