from apps.imports.models import ImportJob
from apps.imports.services import queue_import_job
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .forms import RepairStatusImportForm, SupplyUsageImportForm


def _job_queryset_for_user(user):
    queryset = ImportJob.objects.select_related("uploaded_by").order_by("-created_at")
    if user.role == User.Role.LOGISTICS_MANAGER:
        return queryset.filter(import_type=ImportJob.ImportType.SUPPLY_USAGE)
    if user.role == User.Role.REPAIR_STAFF:
        return queryset.filter(import_type=ImportJob.ImportType.REPAIR_STATUS)
    return queryset


def _history_fragment_html(request):
    return render_to_string(
        "imports/partials/history.html",
        {
            "jobs": _job_queryset_for_user(request.user)[:25],
            "show_history_link": True,
        },
        request=request,
    )


def _render_history_response(request):
    return HttpResponse(_history_fragment_html(request))


class ImportWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "imports/index.html"
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.REPAIR_STAFF,
        User.Role.SUPER_ADMIN,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "jobs": _job_queryset_for_user(self.request.user)[:25],
                "supply_form": SupplyUsageImportForm(),
                "repair_form": RepairStatusImportForm(),
                "show_history_link": True,
            }
        )
        return context


class ImportHistoryView(RoleRequiredMixin, TemplateView):
    template_name = "imports/history_page.html"
    allowed_roles = (
        User.Role.LOGISTICS_MANAGER,
        User.Role.REPAIR_STAFF,
        User.Role.SUPER_ADMIN,
    )

    def get(self, request, *args, **kwargs):
        if getattr(request, "htmx", False):
            return _render_history_response(request)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["jobs"] = _job_queryset_for_user(self.request.user)
        return context


class SupplyUsageImportView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.LOGISTICS_MANAGER, User.Role.SUPER_ADMIN)

    def post(self, request, *args, **kwargs):
        form = SupplyUsageImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_text = form.cleaned_data["file"].read().decode("utf-8")
            queue_import_job(
                uploaded_by=request.user,
                import_type=ImportJob.ImportType.SUPPLY_USAGE,
                original_filename=form.cleaned_data["file"].name,
                csv_text=csv_text,
            )
            messages.success(request, "Supply usage import queued.")
            return _render_history_response(request)
        oob = render_to_string(
            "imports/partials/supply_upload_card.html",
            {"supply_form": form, "hx_swap_oob": True},
            request=request,
        )
        return HttpResponse(_history_fragment_html(request) + oob)


class RepairStatusImportView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.REPAIR_STAFF, User.Role.SUPER_ADMIN)

    def post(self, request, *args, **kwargs):
        form = RepairStatusImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_text = form.cleaned_data["file"].read().decode("utf-8")
            queue_import_job(
                uploaded_by=request.user,
                import_type=ImportJob.ImportType.REPAIR_STATUS,
                original_filename=form.cleaned_data["file"].name,
                csv_text=csv_text,
            )
            messages.success(request, "Maintenance import queued.")
            return _render_history_response(request)
        oob = render_to_string(
            "imports/partials/repair_upload_card.html",
            {"repair_form": form, "hx_swap_oob": True},
            request=request,
        )
        return HttpResponse(_history_fragment_html(request) + oob)
