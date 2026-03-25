from datetime import date, timedelta

from apps.imports.models import ImportJob
from apps.inventory.models import RestockAlert, SupplySchedule, SupplyUsageRecord
from apps.maintenance.models import Machine, MachineStatusEvent, RepairAssignment
from apps.payments.models import RevenueLedgerEntry
from apps.stores.models import Region
from apps.stores.selectors import scoped_region_store_options
from apps.sync.models import AuditLog, SyncConflictLog, SyncProjectionState
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin
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
        revenue_entries = RevenueLedgerEntry.objects.filter(
            store__in=visible_stores,
            posted_at__date__gte=date_from,
            posted_at__date__lte=date_to,
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
                order_count=Count("order", distinct=True),
            )
            .order_by("-posted_at__date")[:14]
        )
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
        maintenance_summary_rows = (
            Machine.objects.filter(store__in=visible_stores)
            .values("store__store_code", "store__name")
            .annotate(
                machine_issues=Count(
                    "id",
                    filter=Q(
                        current_status__in=[
                            Machine.Status.WARNING,
                            Machine.Status.ERROR,
                            Machine.Status.OUT_OF_ORDER,
                            Machine.Status.SCHEDULE_SERVICE,
                        ]
                    ),
                    distinct=True,
                ),
                open_assignments=Count(
                    "repair_assignments",
                    filter=Q(
                        repair_assignments__status__in=RepairAssignment.actionable_statuses()
                    ),
                    distinct=True,
                ),
            )
            .order_by("-machine_issues", "-open_assignments", "store__name")[:12]
        )
        order_financial_rows = revenue_entries.select_related(
            "order", "store"
        ).order_by("-posted_at")[:15]
        draft_schedule_rows = (
            SupplySchedule.objects.filter(
                store__in=visible_stores,
                created_by_ai=True,
            )
            .select_related("store", "inventory_item", "approved_by")
            .order_by("-created_at")[:10]
        )
        visible_region_codes = list(visible_regions.values_list("code", flat=True))
        visible_store_ids = [
            str(store_id) for store_id in visible_stores.values_list("id", flat=True)
        ]
        conflict_queryset = SyncConflictLog.objects.all()
        projection_queryset = SyncProjectionState.objects.all()
        if self.request.user.role != User.Role.SUPER_ADMIN:
            conflict_queryset = conflict_queryset.filter(
                Q(
                    receiver_scope_type=SyncProjectionState.ReceiverScope.REGION,
                    receiver_scope_key__in=visible_region_codes,
                )
                | Q(
                    receiver_scope_type=SyncProjectionState.ReceiverScope.STORE,
                    receiver_scope_key__in=visible_store_ids,
                )
            )
            projection_queryset = projection_queryset.filter(
                Q(
                    receiver_scope_type=SyncProjectionState.ReceiverScope.REGION,
                    receiver_scope_key__in=visible_region_codes,
                )
                | Q(
                    receiver_scope_type=SyncProjectionState.ReceiverScope.STORE,
                    receiver_scope_key__in=visible_store_ids,
                )
            )
        context.update(
            {
                "visible_stores": visible_stores,
                "visible_regions": visible_regions,
                "gross_revenue": revenue["gross"] or 0,
                "net_revenue": revenue["net"] or 0,
                "revenue_by_store": revenue_by_store,
                "daily_revenue_rows": daily_revenue_rows,
                "usage_trends": usage_trends,
                "machine_failure_trends": machine_failure_trends,
                "maintenance_summary_rows": maintenance_summary_rows,
                "order_financial_rows": order_financial_rows,
                "draft_schedule_rows": draft_schedule_rows,
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
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
                "recent_imports": (
                    ImportJob.objects.filter(
                        uploaded_by__default_region__code__in=visible_region_codes
                    )
                    .select_related("uploaded_by")
                    .order_by("-created_at")[:8]
                    if self.request.user.role != User.Role.SUPER_ADMIN
                    else ImportJob.objects.select_related("uploaded_by").order_by(
                        "-created_at"
                    )[:8]
                ),
                "sync_conflict_count": conflict_queryset.filter(
                    resolution_status=SyncConflictLog.ResolutionStatus.OPEN
                ).count(),
                "sync_projection_count": projection_queryset.count(),
                "region_rows": Region.objects.filter(
                    id__in=visible_regions.values("id")
                ).annotate(
                    store_count=Count("stores"),
                    hub_count=Count("supply_hubs"),
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
