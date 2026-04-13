from decimal import Decimal, InvalidOperation

from apps.stores.selectors import scoped_region_store_options, stores_visible_to_user
from apps.users.models import User
from apps.users.permissions import (
    RoleRequiredMixin,
    user_can_manage_store,
    user_has_global_access,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .forms import InventoryAdjustmentForm
from .models import RestockAlert, StoreInventoryBalance
from .selectors import adjustment_step_for_item, group_balances_by_item
from .services import InventoryServiceError, adjust_store_inventory


class InventoryWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "inventory/index.html"
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
        search = self.request.GET.get("search", "").strip()
        balances = StoreInventoryBalance.objects.filter(
            store__in=visible_stores
        ).select_related(
            "store",
            "inventory_item",
        )
        if search:
            balances = balances.filter(inventory_item__name__icontains=search)
        context.update(
            {
                "grouped_balances": group_balances_by_item(
                    user=self.request.user,
                    balances=balances.order_by("inventory_item__name", "store__name"),
                ),
                "low_stock_alerts": RestockAlert.objects.filter(
                    store__in=visible_stores,
                    status=RestockAlert.Status.OPEN,
                ).select_related("store", "inventory_item")[:12],
                "visible_stores": visible_stores,
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
                "search": search,
                "adjustment_form": InventoryAdjustmentForm(),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if getattr(request, "htmx", False):
            html = render_to_string(
                "inventory/partials/balance_table.html", context, request=request
            )
            return HttpResponse(html)
        return self.render_to_response(context)


class InventoryAdjustView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        balance = get_object_or_404(
            StoreInventoryBalance.objects.select_related("store", "inventory_item"),
            pk=kwargs["balance_id"],
        )
        if not (
            user_has_global_access(request.user)
            or user_can_manage_store(request.user, balance.store)
        ):
            raise PermissionDenied(
                "You can only adjust inventory for stores assigned to you."
            )

        post_data = request.POST.copy()
        raw_count = post_data.get("count", "").strip()
        if raw_count:
            try:
                post_data["delta"] = str(Decimal(raw_count) - balance.on_hand_quantity)
            except InvalidOperation:
                pass

        form = InventoryAdjustmentForm(post_data)
        if form.is_valid():
            try:
                adjust_store_inventory(
                    balance=balance,
                    delta=form.cleaned_data["delta"],
                    actor=request.user,
                    reason=form.cleaned_data["reason"],
                )
            except InventoryServiceError as exc:
                form.add_error(None, str(exc))
                adjustment_form = form
            else:
                adjustment_form = InventoryAdjustmentForm()
        else:
            adjustment_form = form

        balance.refresh_from_db()
        available = balance.on_hand_quantity - balance.reserved_quantity
        status = "healthy"
        if balance.on_hand_quantity <= balance.reorder_threshold / 2:
            status = "critical"
        elif balance.on_hand_quantity <= balance.reorder_threshold:
            status = "warning"
        html = render_to_string(
            "inventory/partials/balance_row.html",
            {
                "balance": balance,
                "available": available,
                "status": status,
                "can_adjust": True,
                "adjustment_step": adjustment_step_for_item(balance.inventory_item),
                "adjustment_form": adjustment_form,
            },
            request=request,
        )
        return HttpResponse(html)
