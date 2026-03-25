from apps.analytics.recommendations import explain_maintenance_priority
from apps.imports.models import ImportJob
from apps.stores.selectors import stores_visible_to_user
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from .models import Machine, RepairAssignment


class MaintenanceWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "maintenance/index.html"
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.ADMIN,
        User.Role.REPAIR_STAFF,
        User.Role.SUPER_ADMIN,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visible_stores = stores_visible_to_user(self.request.user)
        status_filter = self.request.GET.get("status", "").strip()
        urgent_machines = Machine.objects.filter(
            store__in=visible_stores
        ).select_related(
            "store",
            "machine_type",
        )
        if status_filter:
            urgent_machines = urgent_machines.filter(current_status=status_filter)
        urgent_machines = urgent_machines.filter(
            current_status__in=[
                Machine.Status.WARNING,
                Machine.Status.ERROR,
                Machine.Status.OUT_OF_ORDER,
                Machine.Status.SCHEDULE_SERVICE,
            ]
        )
        context.update(
            {
                "machines": [
                    {
                        "machine": machine,
                        "explanation": explain_maintenance_priority(machine),
                    }
                    for machine in urgent_machines
                ],
                "assignments": (
                    RepairAssignment.objects.filter(
                        assigned_to=(
                            self.request.user
                            if self.request.user.role == User.Role.REPAIR_STAFF
                            else None
                        )
                    ).select_related("machine", "store", "assigned_to")
                    if self.request.user.role == User.Role.REPAIR_STAFF
                    else RepairAssignment.objects.filter(
                        store__in=visible_stores
                    ).select_related("machine", "store", "assigned_to")
                ),
                "import_jobs": ImportJob.objects.filter(
                    import_type=ImportJob.ImportType.REPAIR_STATUS
                ).select_related("uploaded_by")[:10],
                "status_filter": status_filter,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if getattr(request, "htmx", False):
            html = render_to_string(
                "maintenance/partials/urgent_queue.html", context, request=request
            )
            return HttpResponse(html)
        return self.render_to_response(context)
