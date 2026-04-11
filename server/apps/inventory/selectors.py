from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal

from apps.supply_hubs.models import HubInventoryBalance
from apps.users.permissions import user_can_manage_store, user_has_global_access
from django.db.models import Count, F, Q, Sum

from .models import InventoryItem, RestockAlert, StoreInventoryBalance

WHOLE_NUMBER_UOM_VALUES = {"each", "unit", "count", "item"}
WHOLE_NUMBER_CATEGORIES = {
    InventoryItem.Category.CUPS,
    InventoryItem.Category.LIDS,
    InventoryItem.Category.EQUIPMENT,
    InventoryItem.Category.PACKAGING,
}


def adjustment_step_for_item(inventory_item):
    if not inventory_item:
        return "0.01"
    unit_of_measure = (inventory_item.unit_of_measure or "").strip().lower()
    if unit_of_measure in WHOLE_NUMBER_UOM_VALUES:
        return "1"
    if inventory_item.category in WHOLE_NUMBER_CATEGORIES:
        return "1"
    return "0.01"


def group_balances_by_item(*, user, balances):
    grouped = OrderedDict()
    for balance in balances:
        item_id = balance.inventory_item_id
        group = grouped.setdefault(
            item_id,
            {
                "inventory_item": balance.inventory_item,
                "stores": [],
                "total_on_hand": Decimal("0.00"),
                "total_reserved": Decimal("0.00"),
                "critical_store_count": 0,
            },
        )
        available = balance.on_hand_quantity - balance.reserved_quantity
        status = "healthy"
        if balance.on_hand_quantity <= balance.reorder_threshold / Decimal("2"):
            status = "critical"
            group["critical_store_count"] += 1
        elif balance.on_hand_quantity <= balance.reorder_threshold:
            status = "warning"
        group["stores"].append(
            {
                "balance": balance,
                "available": available,
                "status": status,
                "adjustment_step": adjustment_step_for_item(balance.inventory_item),
                "can_adjust": user_has_global_access(user)
                or user_can_manage_store(user, balance.store),
            }
        )
        group["total_on_hand"] += balance.on_hand_quantity
        group["total_reserved"] += balance.reserved_quantity

    return list(grouped.values())


def build_transfer_recommendations(*, visible_stores, limit=6):
    alerts = (
        RestockAlert.objects.filter(
            store__in=visible_stores,
            status=RestockAlert.Status.OPEN,
            severity__in=[
                RestockAlert.Severity.WARNING,
                RestockAlert.Severity.CRITICAL,
            ],
        )
        .select_related("store", "inventory_item", "store__region")
        .order_by("-created_at")[: limit * 2]
    )
    recommendations = []
    for alert in alerts:
        destination_balance = (
            StoreInventoryBalance.objects.filter(
                store=alert.store,
                inventory_item=alert.inventory_item,
            )
            .select_related("store", "inventory_item")
            .first()
        )
        if not destination_balance:
            continue

        suggested_quantity = max(
            destination_balance.reorder_threshold
            - destination_balance.on_hand_quantity,
            Decimal("1.00"),
        )
        source_balance = (
            StoreInventoryBalance.objects.filter(
                inventory_item=alert.inventory_item,
                store__region=alert.store.region,
                store__in=visible_stores,
            )
            .exclude(store=alert.store)
            .filter(
                on_hand_quantity__gt=destination_balance.reorder_threshold
                * Decimal("1.5")
            )
            .select_related("store")
            .order_by("-on_hand_quantity")
            .first()
        )
        hub_balance = (
            HubInventoryBalance.objects.filter(
                inventory_item=alert.inventory_item,
                hub__region=alert.store.region,
                on_hand_quantity__gt=suggested_quantity,
            )
            .select_related("hub")
            .order_by("-on_hand_quantity")
            .first()
        )

        if source_balance:
            recommendation = {
                "destination_store": alert.store,
                "inventory_item": alert.inventory_item,
                "quantity": suggested_quantity.quantize(Decimal("0.01")),
                "source_label": source_balance.store.name,
                "source_type": "Store transfer",
                "explanation": "A same-region store has enough available stock to cover this gap quickly.",
            }
        elif hub_balance:
            recommendation = {
                "destination_store": alert.store,
                "inventory_item": alert.inventory_item,
                "quantity": suggested_quantity.quantize(Decimal("0.01")),
                "source_label": hub_balance.hub.name,
                "source_type": "Hub transfer",
                "explanation": "The regional hub can cover this shortage without waiting on a local supplier.",
            }
        else:
            recommendation = {
                "destination_store": alert.store,
                "inventory_item": alert.inventory_item,
                "quantity": suggested_quantity.quantize(Decimal("0.01")),
                "source_label": "Local supplier review",
                "source_type": "Supplier fallback",
                "explanation": "No strong internal source is available, so this should move into a supplier workflow.",
            }
        recommendations.append(recommendation)
        if len(recommendations) >= limit:
            break
    return recommendations


def summarize_store_inventory_health(*, visible_stores):
    return (
        StoreInventoryBalance.objects.filter(store__in=visible_stores)
        .values("store__id", "store__name")
        .annotate(
            tracked_items=Count("id"),
            below_threshold=Count(
                "id",
                filter=Q(on_hand_quantity__lte=F("reorder_threshold")),
            ),
            on_hand_total=Sum("on_hand_quantity"),
        )
        .order_by("-below_threshold", "store__name")
    )
