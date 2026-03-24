from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .models import Notification
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin


class NotificationWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "notifications/index.html"
    allowed_roles = tuple(choice for choice, _ in User.Role.choices)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications"] = self.request.user.notifications.order_by("-created_at")
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=kwargs["notification_id"], user=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        html = render_to_string(
            "notifications/partials/list.html",
            {"notifications": request.user.notifications.order_by("-created_at")},
            request=request,
        )
        return HttpResponse(html)
