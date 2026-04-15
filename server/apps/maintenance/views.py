from urllib.parse import urlencode

from apps.imports.models import ImportJob
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin, user_can_manage_machine
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .models import Machine, RepairAssignment
from .selectors import (
    build_assignment_cards,
    build_route_groups,
    build_urgent_machine_rows,
)
from .services import (
    MaintenanceServiceError,
    acknowledge_repair_assignment,
    add_repair_assignment_note,
    auto_assign_machine,
    block_repair_assignment,
    claim_machine_for_repair,
    close_repair_assignment,
    complete_repair_assignment,
    start_repair_assignment,
)


def _visible_import_jobs_for_user(user):
    queryset = ImportJob.objects.filter(
        import_type=ImportJob.ImportType.REPAIR_STATUS
    ).select_related("uploaded_by")
    if user.role == User.Role.REPAIR_STAFF:
        return queryset.filter(uploaded_by=user).order_by("-created_at")[:10]
    return queryset.order_by("-created_at")[:10]


def _workspace_context(request):
    status_filter = (
        request.GET.get("status", "").strip() or request.POST.get("status", "").strip()
    )
    assignments_view_raw = (
        request.GET.get("assignments", "").strip()
        or request.POST.get("assignments", "").strip()
    )
    assignments_view = "all" if assignments_view_raw == "all" else ""
    show_all_assignments = assignments_view == "all"
    assignment_preview_limit = 4
    assignments = build_assignment_cards(request.user)
    assignment_display_items = (
        assignments if show_all_assignments else assignments[:assignment_preview_limit]
    )
    return {
        "machines": build_urgent_machine_rows(
            request.user, status_filter=status_filter
        ),
        "assignments": assignments,
        "assignment_display_items": assignment_display_items,
        "assignment_display_count": len(assignment_display_items),
        "assignment_preview_limit": assignment_preview_limit,
        "assignment_view": assignments_view,
        "show_all_assignments": show_all_assignments,
        "route_groups": build_route_groups(assignments),
        "import_jobs": _visible_import_jobs_for_user(request.user),
        "status_filter": status_filter,
    }


def _render_workspace_response(request):
    context = _workspace_context(request)
    html = render_to_string(
        "maintenance/partials/workspace.html",
        context,
        request=request,
    )
    return HttpResponse(html)


def _render_assignment_section_response(request):
    context = _workspace_context(request)
    context["include_messages"] = True
    html = render_to_string(
        "maintenance/partials/assignment_section.html",
        context,
        request=request,
    )
    return HttpResponse(html)


def _workspace_redirect(request):
    status_filter = request.POST.get("status", "").strip()
    assignments_view = (
        "all" if request.POST.get("assignments", "").strip() == "all" else ""
    )
    url = reverse("maintenance:index")
    query = {}
    if status_filter:
        query["status"] = status_filter
    if assignments_view:
        query["assignments"] = assignments_view
    if query:
        url = f"{url}?{urlencode(query)}"
    return redirect(url)


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
        context.update(_workspace_context(self.request))
        return context

    def get(self, request, *args, **kwargs):
        if getattr(request, "htmx", False):
            return _render_workspace_response(request)
        return super().get(request, *args, **kwargs)


class MaintenanceMachineAssignView(RoleRequiredMixin, View):
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.ADMIN,
        User.Role.REPAIR_STAFF,
        User.Role.SUPER_ADMIN,
    )

    def post(self, request, *args, **kwargs):
        machine = get_object_or_404(
            Machine.objects.select_related("store", "machine_type"),
            pk=kwargs["machine_id"],
        )
        if not user_can_manage_machine(request.user, machine):
            raise PermissionDenied("You can only assign repair work for your stores.")

        try:
            if request.user.role == User.Role.REPAIR_STAFF:
                assignment = claim_machine_for_repair(machine, actor=request.user)
            else:
                assignment = auto_assign_machine(machine, actor=request.user)
            if assignment is None:
                messages.error(
                    request,
                    "No available repair staff found for that machine.",
                )
        except MaintenanceServiceError as exc:
            messages.error(request, str(exc))

        if not getattr(request, "htmx", False):
            return _workspace_redirect(request)
        return _render_workspace_response(request)


class RepairAssignmentActionView(RoleRequiredMixin, View):
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.ADMIN,
        User.Role.REPAIR_STAFF,
        User.Role.SUPER_ADMIN,
    )

    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(
            RepairAssignment.objects.select_related("machine", "store", "assigned_to"),
            pk=kwargs["assignment_id"],
        )
        if not user_can_manage_machine(request.user, assignment.machine):
            raise PermissionDenied("You can only update repair work for your stores.")

        action = request.POST.get("action", "").strip()
        note = request.POST.get("note", "").strip()
        follow_up_required = request.POST.get("follow_up_required") == "on"

        try:
            if action == "acknowledge":
                acknowledge_repair_assignment(assignment, actor=request.user, note=note)
            elif action == "start":
                start_repair_assignment(assignment, actor=request.user, note=note)
            elif action == "block":
                block_repair_assignment(
                    assignment,
                    actor=request.user,
                    note=note,
                    follow_up_required=follow_up_required,
                )
            elif action == "update":
                add_repair_assignment_note(
                    assignment,
                    actor=request.user,
                    note=note,
                    follow_up_required=follow_up_required,
                )
            elif action == "complete":
                complete_repair_assignment(assignment, actor=request.user, note=note)
            elif action == "close":
                close_repair_assignment(assignment, actor=request.user, note=note)
            else:
                raise MaintenanceServiceError("Unsupported repair assignment action.")
        except MaintenanceServiceError as exc:
            messages.error(request, str(exc))

        if not getattr(request, "htmx", False):
            return _workspace_redirect(request)
        return _render_assignment_section_response(request)
