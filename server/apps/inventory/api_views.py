import json
from decimal import Decimal, InvalidOperation

from apps.stores.selectors import stores_visible_to_user
from apps.users.models import User
from apps.users.permissions import user_can_manage_store, user_has_global_access
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from .models import StoreInventoryBalance
from .services import InventoryServiceError, adjust_store_inventory

REPORT_ALLOWED_ROLES = {
    User.Role.MANAGER,
    User.Role.ADMIN,
    User.Role.LOGISTICS_MANAGER,
    User.Role.SUPER_ADMIN,
}
MUTATION_ALLOWED_ROLES = {
    User.Role.MANAGER,
    User.Role.ADMIN,
    User.Role.SUPER_ADMIN,
}


def _require_authenticated_role(request, *, allowed_roles):
    if not getattr(request.user, "is_authenticated", False):
        return JsonResponse({"detail": "Authentication required."}, status=401)
    if getattr(request.user, "role", None) not in allowed_roles:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    return None


class BackendInventoryReportView(View):
    def get(self, request, *args, **kwargs):
        denied = _require_authenticated_role(
            request,
            allowed_roles=REPORT_ALLOWED_ROLES,
        )
        if denied:
            return denied

        balances = list(
            StoreInventoryBalance.objects.filter(
                store__in=stores_visible_to_user(request.user)
            ).select_related("store", "inventory_item")
        )
        payload = {
            "inventory_items": [
                {
                    "balance_id": str(balance.id),
                    "store_code": balance.store.store_code,
                    "inventory_sku": balance.inventory_item.sku,
                    "item_name": balance.inventory_item.name,
                    "quantity": str(balance.on_hand_quantity),
                    "threshold_level": str(balance.reorder_threshold),
                }
                for balance in balances
            ],
            "total_items": len(balances),
            "out_of_stock": sum(
                1 for balance in balances if balance.on_hand_quantity == 0
            ),
            "below_threshold": sum(
                1
                for balance in balances
                if balance.on_hand_quantity <= balance.reorder_threshold
            ),
        }
        return JsonResponse(payload, status=200)


class BackendInventoryMutationView(View):
    def patch(self, request, *args, **kwargs):
        denied = _require_authenticated_role(
            request,
            allowed_roles=MUTATION_ALLOWED_ROLES,
        )
        if denied:
            return denied

        balance = get_object_or_404(
            StoreInventoryBalance.objects.select_related("store", "inventory_item"),
            pk=kwargs["balance_id"],
        )
        if not (
            user_has_global_access(request.user)
            or user_can_manage_store(request.user, balance.store)
        ):
            return JsonResponse({"detail": "Forbidden."}, status=403)

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

        used_quantity_raw = payload.get("used_quantity")
        try:
            used_quantity = Decimal(str(used_quantity_raw))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse(
                {"detail": "used_quantity must be a positive number."},
                status=400,
            )
        if used_quantity <= 0:
            return JsonResponse(
                {"detail": "used_quantity must be a positive number."},
                status=400,
            )

        try:
            adjust_store_inventory(
                balance=balance,
                delta=-used_quantity,
                actor=request.user,
                reason="Backend inventory usage update.",
            )
        except InventoryServiceError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)

        balance.refresh_from_db()
        return JsonResponse(
            {
                "balance_id": str(balance.id),
                "quantity": str(balance.on_hand_quantity),
                "threshold_level": str(balance.reorder_threshold),
            },
            status=200,
        )
