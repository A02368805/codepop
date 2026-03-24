from __future__ import annotations

from apps.inventory.models import SupplyUsageRecord
from apps.maintenance.services import resolve_effective_policy
from apps.orders.personalization import recommend_drink_menu_scores


def recommend_drinks_for_user(user, *, limit=4):
    return recommend_drink_menu_scores(user)[:limit]


def explain_supply_schedule(schedule):
    latest_usage = (
        SupplyUsageRecord.objects.filter(
            store=schedule.store,
            inventory_item=schedule.inventory_item,
        )
        .order_by("-usage_date")
        .first()
    )
    if latest_usage:
        return (
            f"Drafted from recent usage of {latest_usage.quantity_used} "
            f"{schedule.inventory_item.unit_of_measure} on {latest_usage.usage_date}."
        )
    return "Drafted from low-stock heuristics and current threshold settings."


def explain_maintenance_priority(machine):
    policy = resolve_effective_policy(machine)
    if machine.current_status == machine.Status.OUT_OF_ORDER:
        return "Machine is already out of order and should be handled immediately."
    if machine.current_status == machine.Status.ERROR:
        return "Machine reported an error state and needs urgent review."
    if machine.current_status == machine.Status.WARNING and machine.current_status_date:
        return (
            f"Warning window is {policy['warning_shutdown_days']} day(s); "
            f"current warning started on {machine.current_status_date}."
        )
    return "Machine is currently stable but remains in the active maintenance pool."
