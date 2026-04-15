from datetime import date, timedelta

from apps.inventory.models import RestockAlert, SupplySchedule, SupplyUsageRecord
from apps.maintenance.models import Machine, MachineStatusEvent, RepairAssignment
from apps.payments.models import RevenueLedgerEntry
from apps.stores.models import Region
from apps.stores.selectors import scoped_region_store_options
from apps.sync.models import AuditLog
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin, user_can_view_payments_workspace
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import TemplateView, View

from .selectors import build_dashboard_payload


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class AnalyticsWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "analytics/index.html"
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.ADMIN,
        User.Role.LOGISTICS_MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = scoped_region_store_options(
            self.request.user,
            region_id=self.request.GET.get("region", "").strip(),
            store_id=self.request.GET.get("store", "").strip(),
        )
        visible_stores = scope["active_store_scope"]
        visible_regions = scope["region_options"]
        date_from = _parse_date(self.request.GET.get("date_from", "").strip()) or (
            timezone.now().date() - timedelta(days=30)
        )
        date_to = (
            _parse_date(self.request.GET.get("date_to", "").strip())
            or timezone.now().date()
        )
        order_search = self.request.GET.get("order_search", "").strip()
        revenue_entries = RevenueLedgerEntry.objects.filter(
            store__in=visible_stores,
            posted_at__date__gte=date_from,
            posted_at__date__lte=date_to,
        )
        if order_search:
            revenue_entries = revenue_entries.filter(
                Q(order__public_order_code__icontains=order_search)
                | Q(order__locker_code__icontains=order_search)
            )
        revenue = revenue_entries.aggregate(
            gross=Sum("gross_amount"),
            net=Sum("net_amount"),
        )
        revenue_by_store = (
            revenue_entries.values("store__store_code", "store__name")
            .annotate(gross=Sum("gross_amount"), net=Sum("net_amount"))
            .order_by("-net")[:10]
        )
        daily_revenue_rows = (
            revenue_entries.values("posted_at__date")
            .annotate(
                gross=Sum("gross_amount"),
                net=Sum("net_amount"),
                row_count=Count("id"),
            )
            .order_by("-posted_at__date")[:14]
        )
        revenue_ledger_rows = revenue_entries.select_related("store", "order").order_by(
            "-posted_at"
        )[:20]
        usage_trends = (
            SupplyUsageRecord.objects.filter(
                store__in=visible_stores,
                usage_date__gte=date_from,
                usage_date__lte=date_to,
            )
            .values("inventory_item__name")
            .annotate(
                total_used=Sum("quantity_used"),
                store_count=Count("store", distinct=True),
            )
            .order_by("-total_used")[:10]
        )
        machine_failure_trends = (
            MachineStatusEvent.objects.filter(
                machine__store__in=visible_stores,
                status__in=[
                    Machine.Status.WARNING,
                    Machine.Status.ERROR,
                    Machine.Status.OUT_OF_ORDER,
                ],
                status_date__gte=date_from,
                status_date__lte=date_to,
            )
            .values("machine__store__name", "status")
            .annotate(event_count=Count("id"))
            .order_by("-event_count")[:12]
        )
        machine_status_summary = (
            Machine.objects.filter(store__in=visible_stores)
            .values("current_status")
            .annotate(count=Count("id"))
            .order_by("-count", "current_status")
        )
        assignment_status_summary = (
            RepairAssignment.objects.filter(store__in=visible_stores)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("-count", "status")
        )
        ai_schedule_rows = (
            SupplySchedule.objects.filter(store__in=visible_stores, created_by_ai=True)
            .select_related("store", "inventory_item", "approved_by")
            .order_by("-updated_at")[:12]
        )
        context.update(
            {
                "visible_stores": visible_stores,
                "visible_regions": visible_regions,
                "gross_revenue": revenue["gross"] or 0,
                "net_revenue": revenue["net"] or 0,
                "revenue_by_store": revenue_by_store,
                "daily_revenue_rows": daily_revenue_rows,
                "revenue_ledger_rows": revenue_ledger_rows,
                "usage_trends": usage_trends,
                "machine_failure_trends": machine_failure_trends,
                "machine_status_summary": machine_status_summary,
                "assignment_status_summary": assignment_status_summary,
                "ai_schedule_rows": ai_schedule_rows,
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "order_search": order_search,
                "open_alerts": RestockAlert.objects.filter(
                    store__in=visible_stores, status=RestockAlert.Status.OPEN
                ).count(),
                "machine_issues": Machine.objects.filter(
                    store__in=visible_stores,
                    current_status__in=[
                        Machine.Status.WARNING,
                        Machine.Status.ERROR,
                        Machine.Status.OUT_OF_ORDER,
                    ],
                ).count(),
                "audit_logs": (
                    AuditLog.objects.filter(store__in=visible_stores).select_related(
                        "actor", "store", "region"
                    )[:20]
                    if self.request.user.role != User.Role.SUPER_ADMIN
                    else AuditLog.objects.select_related("actor", "store", "region")[
                        :20
                    ]
                ),
                "region_rows": Region.objects.filter(
                    id__in=visible_regions.values("id")
                ).annotate(
                    store_count=Count("stores"),
                    hub_count=Count("supply_hubs"),
                ),
                "can_view_payments_workspace": user_can_view_payments_workspace(
                    self.request.user
                ),
            }
        )
        return context


class DashboardMetricsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        payload = build_dashboard_payload(request.user, request.user.role)
        html = render_to_string(
            "partials/dashboard_metrics.html",
            {"dashboard": payload},
            request=request,
        )
        return HttpResponse(html)
