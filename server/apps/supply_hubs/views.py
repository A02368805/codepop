from datetime import date, timedelta

from apps.analytics.recommendations import explain_supply_schedule
from apps.inventory.models import (
    LocalSupplier,
    SupplierReplenishment,
    SupplySchedule,
    SupplyUsageRecord,
)
from apps.inventory.selectors import build_transfer_recommendations
from apps.inventory.services import (
    InventoryServiceError,
    approve_supply_schedule,
    cancel_supplier_replenishment,
    create_supplier_replenishment_order,
    create_transfer_request,
    progress_transfer,
    receive_supplier_replenishment,
)
from apps.stores.selectors import scoped_region_store_options
from apps.users.models import User
from apps.users.permissions import (
    RoleRequiredMixin,
    user_can_approve_transfer,
    user_can_progress_transfer,
    user_can_receive_transfer,
)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import SupplierOrderForm, TransferRequestForm
from .models import HubInventoryBalance, SupplyHub, SupplyTransfer

ALLOWED_WORKSPACE_ROLES = (
    User.Role.LOGISTICS_MANAGER,
    User.Role.SUPER_ADMIN,
)


def _decorate_transfer_actions(*, transfers, user):
    decorated = []
    for transfer in transfers:
        transfer.next_action = {
            "label": "",
            "url_name": "",
            "allowed": False,
            "denied_reason": "",
        }
        if transfer.status == SupplyTransfer.Status.REQUESTED:
            transfer.next_action = {
                "label": "Approve",
                "url_name": "supply_hubs:approve-transfer",
                "allowed": user_can_approve_transfer(user, transfer),
                "denied_reason": "Approval requires logistics scope for this destination region.",
            }
        elif transfer.status == SupplyTransfer.Status.APPROVED:
            transfer.next_action = {
                "label": "Reserve",
                "url_name": "supply_hubs:reserve-transfer",
                "allowed": user_can_progress_transfer(user, transfer),
                "denied_reason": "You do not have scope to reserve this transfer.",
            }
        elif transfer.status == SupplyTransfer.Status.RESERVED:
            transfer.next_action = {
                "label": "Ship",
                "url_name": "supply_hubs:ship-transfer",
                "allowed": user_can_progress_transfer(user, transfer),
                "denied_reason": "You do not have scope to ship this transfer.",
            }
        elif transfer.status == SupplyTransfer.Status.IN_TRANSIT:
            transfer.next_action = {
                "label": "Mark delivered",
                "url_name": "supply_hubs:deliver-transfer",
                "allowed": user_can_progress_transfer(user, transfer),
                "denied_reason": "You do not have scope to mark this transfer as delivered.",
            }
        elif transfer.status == SupplyTransfer.Status.DELIVERED:
            transfer.next_action = {
                "label": "Receive",
                "url_name": "supply_hubs:receive-transfer",
                "allowed": user_can_receive_transfer(user, transfer),
                "denied_reason": "You do not have scope to receive this transfer.",
            }
        decorated.append(transfer)
    return decorated


def _request_value(request, key, default=""):
    if request.method == "POST":
        return request.POST.get(key, default)
    return request.GET.get(key, default)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _resolve_window(request):
    window = _request_value(request, "window", "month").strip() or "month"
    today = timezone.now().date()
    if window == "week":
        return window, today - timedelta(days=7), today
    if window == "custom":
        return (
            window,
            _parse_date(_request_value(request, "date_from", "").strip())
            or today - timedelta(days=30),
            _parse_date(_request_value(request, "date_to", "").strip()) or today,
        )
    return window, today - timedelta(days=30), today


def _filtered_supply_context(request, *, transfer_form=None, supplier_order_form=None):
    scope = scoped_region_store_options(
        request.user,
        region_id=_request_value(request, "region", "").strip(),
        store_id=_request_value(request, "store", "").strip(),
    )
    window, date_from, date_to = _resolve_window(request)
    visible_regions = scope["region_options"]
    visible_stores = scope["active_store_scope"]

    transfers = (
        SupplyTransfer.objects.filter(destination_store__in=visible_stores)
        .select_related(
            "destination_store",
            "destination_store__region",
            "source_store",
            "source_hub",
            "requested_by",
            "approved_by",
        )
        .prefetch_related("line_items__inventory_item")
    )
    if date_from:
        transfers = transfers.filter(requested_at__date__gte=date_from)
    if date_to:
        transfers = transfers.filter(requested_at__date__lte=date_to)

    schedules = SupplySchedule.objects.filter(
        store__in=visible_stores,
        created_by_ai=True,
    ).select_related("store", "inventory_item", "approved_by")

    supplier_orders = SupplierReplenishment.objects.filter(
        store__in=visible_stores
    ).select_related(
        "supplier", "store", "inventory_item", "requested_by", "recorded_by"
    )
    if date_from:
        supplier_orders = supplier_orders.filter(ordered_at__date__gte=date_from)
    if date_to:
        supplier_orders = supplier_orders.filter(ordered_at__date__lte=date_to)

    recommendations = build_transfer_recommendations(
        visible_stores=visible_stores,
        limit=8,
    )
    supplier_fallbacks = [
        recommendation
        for recommendation in recommendations
        if recommendation["source_type"] == "Supplier fallback"
    ]

    transfer_rows = list(transfers.order_by("-requested_at"))
    transfer_rows = _decorate_transfer_actions(
        transfers=transfer_rows,
        user=request.user,
    )

    return {
        "scope": scope,
        "window": window,
        "date_from": date_from,
        "date_to": date_to,
        "visible_regions": visible_regions,
        "visible_stores": visible_stores,
        "transfers": transfer_rows,
        "schedule_rows": [
            {"schedule": schedule, "explanation": explain_supply_schedule(schedule)}
            for schedule in schedules.order_by("-created_at")
        ],
        "hubs": SupplyHub.objects.filter(region__in=visible_regions).order_by(
            "hub_code"
        ),
        "hub_balances": HubInventoryBalance.objects.filter(
            hub__region__in=visible_regions
        )
        .select_related("hub", "inventory_item")
        .order_by("hub__name", "inventory_item__name"),
        "suppliers": LocalSupplier.objects.filter(
            service_region__in=visible_regions
        ).order_by("name"),
        "supplier_orders": supplier_orders.order_by("-ordered_at", "-received_at"),
        "transfer_recommendations": recommendations,
        "supplier_fallbacks": supplier_fallbacks,
        "usage_total": (
            SupplyUsageRecord.objects.filter(
                store__in=visible_stores,
                usage_date__gte=date_from,
                usage_date__lte=date_to,
            )
            .aggregate(total=Sum("quantity_used"))
            .get("total")
            if date_from and date_to
            else None
        ),
        "transfer_form": transfer_form or TransferRequestForm(user=request.user),
        "supplier_order_form": supplier_order_form
        or SupplierOrderForm(user=request.user),
    }


def _workspace_context(request, *, transfer_form=None, supplier_order_form=None):
    supply_context = _filtered_supply_context(
        request,
        transfer_form=transfer_form,
        supplier_order_form=supplier_order_form,
    )
    supply_context.update(
        {
            "region_options": supply_context["scope"]["region_options"],
            "store_options": supply_context["scope"]["store_options"],
            "selected_region": supply_context["scope"]["selected_region"],
            "selected_store": supply_context["scope"]["selected_store"],
            "date_from": (
                supply_context["date_from"].isoformat()
                if supply_context["date_from"]
                else ""
            ),
            "date_to": (
                supply_context["date_to"].isoformat()
                if supply_context["date_to"]
                else ""
            ),
        }
    )
    return supply_context


def _render_transfer_table(request, *, error_message=""):
    context = _filtered_supply_context(request)
    html = render_to_string(
        "supply_hubs/partials/transfer_table.html",
        {
            "transfers": context["transfers"],
            "transfer_error": error_message,
        },
        request=request,
    )
    return HttpResponse(html, status=409 if error_message else 200)


def _render_schedule_list(request, *, error_message=""):
    context = _filtered_supply_context(request)
    html = render_to_string(
        "supply_hubs/partials/schedule_list.html",
        {
            "schedule_rows": context["schedule_rows"],
            "schedule_error": error_message,
        },
        request=request,
    )
    return HttpResponse(html, status=409 if error_message else 200)


def _render_supplier_orders(request, *, error_message=""):
    context = _filtered_supply_context(request)
    html = render_to_string(
        "supply_hubs/partials/supplier_order_table.html",
        {
            "supplier_orders": context["supplier_orders"],
            "supplier_order_error": error_message,
        },
        request=request,
    )
    return HttpResponse(html, status=409 if error_message else 200)


def _ensure_workspace_access(request):
    if (
        not getattr(request.user, "is_authenticated", False)
        or request.user.role not in ALLOWED_WORKSPACE_ROLES
    ):
        raise PermissionDenied("You do not have access to the logistics workspace.")


class SupplyHubWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "supply_hubs/index.html"
    allowed_roles = ALLOWED_WORKSPACE_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_workspace_context(self.request))
        return context


class TransferTableView(RoleRequiredMixin, TemplateView):
    template_name = "supply_hubs/partials/transfer_table.html"
    allowed_roles = ALLOWED_WORKSPACE_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transfers"] = _filtered_supply_context(self.request)["transfers"]
        return context


class TransferCreateView(View):
    def post(self, request, *args, **kwargs):
        _ensure_workspace_access(request)
        transfer_form = TransferRequestForm(request.POST, user=request.user)
        supplier_order_form = SupplierOrderForm(user=request.user)
        if transfer_form.is_valid():
            try:
                transfer = create_transfer_request(
                    actor=request.user,
                    destination_store=transfer_form.cleaned_data["destination_store"],
                    inventory_item=transfer_form.cleaned_data["inventory_item"],
                    quantity_requested=transfer_form.cleaned_data["quantity_requested"],
                    source_kind=transfer_form.cleaned_data["source_kind"],
                    source_store=transfer_form.cleaned_data.get("source_store"),
                    source_hub=transfer_form.cleaned_data.get("source_hub"),
                    notes=transfer_form.cleaned_data.get("notes", ""),
                )
            except InventoryServiceError as exc:
                transfer_form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Transfer requested for {transfer.destination_store.name}.",
                )
                return redirect("supply_hubs:index")

        context = _workspace_context(
            request,
            transfer_form=transfer_form,
            supplier_order_form=supplier_order_form,
        )
        return render(request, "supply_hubs/index.html", context, status=400)


class TransferActionView(View):
    action = ""

    def post(self, request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            raise PermissionDenied("Sign in to manage transfers.")
        transfer = get_object_or_404(
            SupplyTransfer.objects.select_related(
                "destination_store",
                "destination_store__region",
                "source_store",
                "source_hub",
            ).prefetch_related("line_items__inventory_item"),
            pk=kwargs["transfer_id"],
        )
        try:
            progress_transfer(transfer, actor=request.user, action=self.action)
        except InventoryServiceError as exc:
            return _render_transfer_table(request, error_message=str(exc))
        return _render_transfer_table(request)


class TransferApproveView(TransferActionView):
    action = "approve"


class TransferReserveView(TransferActionView):
    action = "reserve"


class TransferShipView(TransferActionView):
    action = "ship"


class TransferDeliverView(TransferActionView):
    action = "deliver"


class TransferReceiveView(TransferActionView):
    action = "receive"


class SupplyScheduleListView(RoleRequiredMixin, TemplateView):
    template_name = "supply_hubs/partials/schedule_list.html"
    allowed_roles = ALLOWED_WORKSPACE_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["schedule_rows"] = _filtered_supply_context(self.request)[
            "schedule_rows"
        ]
        return context


class SupplyScheduleApproveView(View):
    def post(self, request, *args, **kwargs):
        _ensure_workspace_access(request)
        schedule = get_object_or_404(SupplySchedule, pk=kwargs["schedule_id"])
        try:
            approve_supply_schedule(schedule, approver=request.user)
        except InventoryServiceError as exc:
            return _render_schedule_list(request, error_message=str(exc))
        return _render_schedule_list(request)


class SupplierOrderListView(RoleRequiredMixin, TemplateView):
    template_name = "supply_hubs/partials/supplier_order_table.html"
    allowed_roles = ALLOWED_WORKSPACE_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["supplier_orders"] = _filtered_supply_context(self.request)[
            "supplier_orders"
        ]
        return context


class SupplierOrderCreateView(View):
    def post(self, request, *args, **kwargs):
        _ensure_workspace_access(request)
        supplier_order_form = SupplierOrderForm(request.POST, user=request.user)
        transfer_form = TransferRequestForm(user=request.user)
        if supplier_order_form.is_valid():
            try:
                replenishment = create_supplier_replenishment_order(
                    actor=request.user,
                    supplier=supplier_order_form.cleaned_data["supplier"],
                    store=supplier_order_form.cleaned_data["store"],
                    inventory_item=supplier_order_form.cleaned_data["inventory_item"],
                    quantity_requested=supplier_order_form.cleaned_data[
                        "quantity_requested"
                    ],
                    expected_delivery_date=supplier_order_form.cleaned_data.get(
                        "expected_delivery_date"
                    ),
                    unit_cost=supplier_order_form.cleaned_data.get("unit_cost"),
                    notes=supplier_order_form.cleaned_data.get("notes", ""),
                )
            except InventoryServiceError as exc:
                supplier_order_form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Supplier order placed with {replenishment.supplier.name}.",
                )
                return redirect("supply_hubs:index")

        context = _workspace_context(
            request,
            transfer_form=transfer_form,
            supplier_order_form=supplier_order_form,
        )
        return render(request, "supply_hubs/index.html", context, status=400)


class SupplierOrderReceiveView(View):
    def post(self, request, *args, **kwargs):
        _ensure_workspace_access(request)
        replenishment = get_object_or_404(
            SupplierReplenishment.objects.select_related(
                "store", "store__region", "inventory_item"
            ),
            pk=kwargs["replenishment_id"],
        )
        try:
            receive_supplier_replenishment(replenishment, actor=request.user)
        except InventoryServiceError as exc:
            return _render_supplier_orders(request, error_message=str(exc))
        return _render_supplier_orders(request)


class SupplierOrderCancelView(View):
    def post(self, request, *args, **kwargs):
        _ensure_workspace_access(request)
        replenishment = get_object_or_404(
            SupplierReplenishment.objects.select_related("store", "store__region"),
            pk=kwargs["replenishment_id"],
        )
        try:
            cancel_supplier_replenishment(replenishment, actor=request.user)
        except InventoryServiceError as exc:
            return _render_supplier_orders(request, error_message=str(exc))
        return _render_supplier_orders(request)
