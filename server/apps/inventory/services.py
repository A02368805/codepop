from __future__ import annotations

from decimal import Decimal

from apps.inventory.models import InventoryItem
from apps.stores.utils import haversine_miles
from apps.supply_hubs.models import (
    HubInventoryBalance,
    SupplyTransfer,
    SupplyTransferLineItem,
)
from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance
from apps.users.permissions import (
    user_can_approve_transfer,
    user_can_manage_supplier_order,
    user_can_progress_transfer,
    user_can_receive_transfer,
    user_can_request_transfer,
)
from core.exceptions import ServiceError
from django.db import transaction
from django.utils import timezone

from .models import (
    RestockAlert,
    StoreInventoryBalance,
    SupplierReplenishment,
    SupplySchedule,
)


class InventoryServiceError(ServiceError):
    pass


def _as_decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def pack_size_for_item(inventory_item):
    pack_sizes = {
        InventoryItem.Category.CUPS: Decimal("250"),
        InventoryItem.Category.LIDS: Decimal("250"),
        InventoryItem.Category.SODA: Decimal("24"),
        InventoryItem.Category.SYRUP: Decimal("12"),
        InventoryItem.Category.ADD_IN: Decimal("12"),
        InventoryItem.Category.ICE_CREAM: Decimal("8"),
        InventoryItem.Category.DAIRY: Decimal("8"),
        InventoryItem.Category.PACKAGING: Decimal("100"),
    }
    return pack_sizes.get(inventory_item.category, Decimal("10"))


def recommended_bulk_quantity(inventory_item, projected_usage):
    pack_size = pack_size_for_item(inventory_item)
    target_quantity = max(
        _as_decimal(projected_usage) * Decimal("3"),
        inventory_item.default_low_stock_threshold * Decimal("2"),
        pack_size,
    )
    remainder = target_quantity % pack_size
    if remainder:
        target_quantity += pack_size - remainder
    return target_quantity


def normalize_bulk_order_quantity(inventory_item, requested_quantity):
    pack_size = pack_size_for_item(inventory_item)
    target_quantity = max(_as_decimal(requested_quantity), pack_size)
    remainder = target_quantity % pack_size
    if remainder:
        target_quantity += pack_size - remainder
    return target_quantity


def get_store_balance(store, inventory_item):
    balance, _ = StoreInventoryBalance.objects.get_or_create(
        store=store,
        inventory_item=inventory_item,
        defaults={"reorder_threshold": inventory_item.default_low_stock_threshold},
    )
    return balance


def get_hub_balance(hub, inventory_item):
    balance, _ = HubInventoryBalance.objects.get_or_create(
        hub=hub,
        inventory_item=inventory_item,
    )
    return balance


def available_quantity(balance) -> Decimal:
    return balance.on_hand_quantity - balance.reserved_quantity


def apply_balance_change(
    balance, *, on_hand_delta=Decimal("0.00"), reserved_delta=Decimal("0.00")
):
    new_on_hand = balance.on_hand_quantity + _as_decimal(on_hand_delta)
    new_reserved = balance.reserved_quantity + _as_decimal(reserved_delta)
    if new_on_hand < 0 or new_reserved < 0 or new_reserved > new_on_hand:
        raise InventoryServiceError(
            "Inventory mutation would result in invalid quantities."
        )
    balance.on_hand_quantity = new_on_hand
    balance.reserved_quantity = new_reserved
    balance.save()
    return balance


def evaluate_restock_alert(balance):
    if balance.on_hand_quantity > balance.reorder_threshold:
        RestockAlert.objects.filter(
            store=balance.store,
            inventory_item=balance.inventory_item,
            status=RestockAlert.Status.OPEN,
        ).update(status=RestockAlert.Status.RESOLVED, resolved_at=timezone.now())
        return None

    severity = (
        RestockAlert.Severity.CRITICAL
        if balance.on_hand_quantity <= balance.reorder_threshold / Decimal("2")
        else RestockAlert.Severity.WARNING
    )
    alert, _ = RestockAlert.objects.update_or_create(
        store=balance.store,
        inventory_item=balance.inventory_item,
        status=RestockAlert.Status.OPEN,
        defaults={"severity": severity, "triggered_by": "threshold"},
    )
    return alert


def _inventory_item_for_reservation(*, sku):
    inventory_item = InventoryItem.objects.filter(sku=sku).first()
    if inventory_item:
        return inventory_item

    from apps.orders.catalog import catalog_inventory_definitions

    known_catalog_skus = {row[0] for row in catalog_inventory_definitions()}
    if sku in known_catalog_skus:
        raise InventoryServiceError(
            "This environment is missing part of the current inventory catalog. "
            "Run `python manage.py bootstrap_demo_data --reset` and then rebuild the cart."
        )
    raise InventoryServiceError(
        "This cart contains an outdated recipe snapshot. Clear the cart and build the drink again."
    )


def _locked_store_balance(*, store, inventory_item):
    balance = get_store_balance(store, inventory_item)
    return StoreInventoryBalance.objects.select_for_update().get(pk=balance.pk)


def _locked_hub_balance(*, hub, inventory_item):
    balance = get_hub_balance(hub, inventory_item)
    return HubInventoryBalance.objects.select_for_update().get(pk=balance.pk)


def _lock_transfer(transfer):
    return SupplyTransfer.objects.select_for_update().get(pk=transfer.pk)


def _locked_transfer_line_items(transfer):
    return SupplyTransferLineItem.objects.select_for_update().filter(transfer=transfer)


@transaction.atomic
def reserve_order_inventory(order):
    for item in order.items.all():
        requirements = item.customizations_json.get("inventory_requirements", [])
        for requirement in requirements:
            sku = requirement.get("sku")
            quantity = _as_decimal(requirement.get("quantity", 0))
            if quantity <= 0:
                continue
            inventory_item = _inventory_item_for_reservation(sku=sku)
            balance = _locked_store_balance(
                store=order.store,
                inventory_item=inventory_item,
            )
            if available_quantity(balance) < quantity:
                raise InventoryServiceError(f"Insufficient inventory for SKU '{sku}'.")
            apply_balance_change(balance, on_hand_delta=-quantity)
            evaluate_restock_alert(balance)


@transaction.atomic
def reverse_order_inventory(order):
    for item in order.items.all():
        requirements = item.customizations_json.get("inventory_requirements", [])
        for requirement in requirements:
            sku = requirement.get("sku")
            quantity = _as_decimal(requirement.get("quantity", 0))
            if quantity <= 0:
                continue
            inventory_item = _inventory_item_for_reservation(sku=sku)
            balance = _locked_store_balance(
                store=order.store,
                inventory_item=inventory_item,
            )
            apply_balance_change(balance, on_hand_delta=quantity)
            evaluate_restock_alert(balance)


def determine_transfer_scope(*, source_store=None, source_hub=None, destination_store):
    if bool(source_store) == bool(source_hub):
        raise InventoryServiceError("A transfer must have exactly one source.")

    if source_store:
        if source_store.region_id != destination_store.region_id:
            raise InventoryServiceError(
                "Direct store-to-store transfers are only allowed within the same region."
            )
        return (
            SupplyTransfer.TransferScope.SAME_REGION_STORE,
            haversine_miles(
                source_store.latitude,
                source_store.longitude,
                destination_store.latitude,
                destination_store.longitude,
            ),
        )

    distance = haversine_miles(
        source_hub.latitude,
        source_hub.longitude,
        destination_store.latitude,
        destination_store.longitude,
    )
    if source_hub.region_id == destination_store.region_id:
        return SupplyTransfer.TransferScope.HUB_TO_STORE, distance
    if distance <= Decimal("1000"):
        return SupplyTransfer.TransferScope.CROSS_REGION_HUB, distance
    raise InventoryServiceError(
        "Cross-region hub deliveries are limited to destinations within 1000 miles."
    )


def choose_internal_transfer_source(
    *, destination_store, inventory_item, quantity_requested
):
    quantity_requested = _as_decimal(quantity_requested)
    if quantity_requested <= 0:
        raise InventoryServiceError("Transfer quantities must be positive.")

    source_store_balance = (
        StoreInventoryBalance.objects.filter(
            store__region=destination_store.region,
            inventory_item=inventory_item,
        )
        .exclude(store=destination_store)
        .select_related("store")
        .order_by("-on_hand_quantity")
        .first()
    )
    if (
        source_store_balance
        and available_quantity(source_store_balance) >= quantity_requested
    ):
        return {
            "source_store": source_store_balance.store,
            "source_hub": None,
            "summary": f"Using same-region store stock from {source_store_balance.store.name}.",
        }

    regional_hub_balance = (
        HubInventoryBalance.objects.filter(
            hub__region=destination_store.region,
            inventory_item=inventory_item,
        )
        .select_related("hub")
        .order_by("-on_hand_quantity")
        .first()
    )
    if (
        regional_hub_balance
        and available_quantity(regional_hub_balance) >= quantity_requested
    ):
        return {
            "source_store": None,
            "source_hub": regional_hub_balance.hub,
            "summary": f"Using the regional hub {regional_hub_balance.hub.name}.",
        }

    eligible_hub = None
    eligible_distance = None
    for hub_balance in (
        HubInventoryBalance.objects.filter(inventory_item=inventory_item)
        .exclude(hub__region=destination_store.region)
        .select_related("hub", "hub__region")
        .order_by("-on_hand_quantity")
    ):
        if available_quantity(hub_balance) < quantity_requested:
            continue
        distance = haversine_miles(
            hub_balance.hub.latitude,
            hub_balance.hub.longitude,
            destination_store.latitude,
            destination_store.longitude,
        )
        if distance <= Decimal("1000") and (
            eligible_distance is None or distance < eligible_distance
        ):
            eligible_hub = hub_balance.hub
            eligible_distance = distance

    if eligible_hub:
        return {
            "source_store": None,
            "source_hub": eligible_hub,
            "summary": f"Using eligible cross-region hub stock from {eligible_hub.name}.",
        }

    raise InventoryServiceError(
        "No eligible internal source is available for this item. Use the supplier ordering workflow."
    )


def create_transfer_request(
    *,
    actor,
    destination_store,
    inventory_item,
    quantity_requested,
    source_kind="auto",
    source_store=None,
    source_hub=None,
    notes="",
    is_ai_draft=False,
):
    if not user_can_request_transfer(actor, destination_store):
        raise InventoryServiceError(
            "You cannot request a transfer for that destination store."
        )

    quantity_requested = _as_decimal(quantity_requested)
    if quantity_requested <= 0:
        raise InventoryServiceError("Transfer quantities must be positive.")

    summary_note = ""
    if source_kind == "auto":
        source_selection = choose_internal_transfer_source(
            destination_store=destination_store,
            inventory_item=inventory_item,
            quantity_requested=quantity_requested,
        )
        source_store = source_selection["source_store"]
        source_hub = source_selection["source_hub"]
        summary_note = source_selection["summary"]
    elif source_kind == "store":
        if source_store is None:
            raise InventoryServiceError("Pick a source store for this transfer.")
    elif source_kind == "hub":
        if source_hub is None:
            raise InventoryServiceError("Pick a source hub for this transfer.")
    else:
        raise InventoryServiceError("Unsupported transfer source type.")

    if source_store:
        source_balance = get_store_balance(source_store, inventory_item)
    else:
        source_balance = get_hub_balance(source_hub, inventory_item)
    if available_quantity(source_balance) < quantity_requested:
        raise InventoryServiceError(
            "The chosen source does not have enough available stock."
        )

    combined_notes = "\n".join(
        [part for part in [summary_note, (notes or "").strip()] if part]
    ).strip()
    return request_transfer(
        requested_by=actor,
        destination_store=destination_store,
        source_store=source_store,
        source_hub=source_hub,
        line_items=[
            {
                "inventory_item": inventory_item,
                "quantity_requested": quantity_requested,
            }
        ],
        notes=combined_notes,
        is_ai_draft=is_ai_draft,
    )


@transaction.atomic
def request_transfer(
    *,
    requested_by,
    destination_store,
    line_items,
    source_store=None,
    source_hub=None,
    notes="",
    is_ai_draft=False,
):
    transfer_scope, distance_miles = determine_transfer_scope(
        source_store=source_store,
        source_hub=source_hub,
        destination_store=destination_store,
    )
    transfer = SupplyTransfer.objects.create(
        source_type=(
            SupplyTransfer.SourceType.STORE
            if source_store
            else SupplyTransfer.SourceType.HUB
        ),
        source_store=source_store,
        source_hub=source_hub,
        destination_store=destination_store,
        requested_by=requested_by,
        transfer_scope=transfer_scope,
        distance_miles=distance_miles,
        notes=notes,
        is_ai_draft=is_ai_draft,
    )
    for line in line_items:
        quantity_requested = _as_decimal(line["quantity_requested"])
        if quantity_requested <= 0:
            raise InventoryServiceError("Transfer quantities must be positive.")
        SupplyTransferLineItem.objects.create(
            transfer=transfer,
            inventory_item=line["inventory_item"],
            quantity_requested=quantity_requested,
        )

    create_outbox_event(
        event_type="transfer.requested",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": destination_store.region.code},
    )
    create_audit_log(
        actor=requested_by,
        action="transfer.requested",
        instance=transfer,
        after=serialize_instance(transfer),
    )
    return transfer


@transaction.atomic
def approve_transfer(transfer, *, approver, approved_quantities=None):
    transfer = _lock_transfer(transfer)
    if not user_can_approve_transfer(approver, transfer):
        raise InventoryServiceError("User cannot approve this transfer.")
    if transfer.status != SupplyTransfer.Status.REQUESTED:
        raise InventoryServiceError("Only requested transfers can be approved.")

    approved_quantities = approved_quantities or {}
    for line_item in _locked_transfer_line_items(transfer):
        quantity_approved = _as_decimal(
            approved_quantities.get(
                str(line_item.inventory_item_id), line_item.quantity_requested
            )
        )
        if quantity_approved <= 0:
            raise InventoryServiceError(
                "Approved transfer quantities must be positive."
            )
        if quantity_approved > line_item.quantity_requested:
            raise InventoryServiceError(
                "Approved transfer quantity cannot exceed requested quantity."
            )
        line_item.quantity_approved = quantity_approved
        line_item.save()

    before = serialize_instance(transfer)
    transfer.status = SupplyTransfer.Status.APPROVED
    transfer.approved_by = approver
    transfer.approved_at = timezone.now()
    transfer.save()
    create_outbox_event(
        event_type="transfer.approved",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": transfer.destination_store.region.code},
        entity_version=2,
    )
    create_audit_log(
        actor=approver,
        action="transfer.approved",
        instance=transfer,
        before=before,
        after=serialize_instance(transfer),
    )
    return transfer


@transaction.atomic
def reserve_transfer_inventory(transfer):
    transfer = _lock_transfer(transfer)
    if transfer.status != SupplyTransfer.Status.APPROVED:
        raise InventoryServiceError("Only approved transfers can reserve stock.")

    for line_item in _locked_transfer_line_items(transfer):
        quantity = line_item.quantity_approved
        if quantity <= 0:
            raise InventoryServiceError(
                "Approved transfer quantities must be positive before reservation."
            )
        if transfer.source_store_id:
            balance = _locked_store_balance(
                store=transfer.source_store,
                inventory_item=line_item.inventory_item,
            )
        else:
            balance = _locked_hub_balance(
                hub=transfer.source_hub,
                inventory_item=line_item.inventory_item,
            )
        if available_quantity(balance) < quantity:
            raise InventoryServiceError(
                "Transfer would oversubscribe source inventory."
            )
        apply_balance_change(balance, reserved_delta=quantity)

    before = serialize_instance(transfer)
    transfer.status = SupplyTransfer.Status.RESERVED
    transfer.save()
    create_outbox_event(
        event_type="transfer.reserved",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": transfer.destination_store.region.code},
        entity_version=3,
    )
    create_audit_log(
        action="transfer.reserved",
        instance=transfer,
        before=before,
        after=serialize_instance(transfer),
    )
    return transfer


@transaction.atomic
def ship_transfer(transfer):
    transfer = _lock_transfer(transfer)
    if transfer.status != SupplyTransfer.Status.RESERVED:
        raise InventoryServiceError("Only reserved transfers can be shipped.")

    for line_item in _locked_transfer_line_items(transfer):
        quantity = line_item.quantity_approved
        if transfer.source_store_id:
            balance = _locked_store_balance(
                store=transfer.source_store,
                inventory_item=line_item.inventory_item,
            )
        else:
            balance = _locked_hub_balance(
                hub=transfer.source_hub,
                inventory_item=line_item.inventory_item,
            )
        apply_balance_change(balance, on_hand_delta=-quantity, reserved_delta=-quantity)

    before = serialize_instance(transfer)
    transfer.status = SupplyTransfer.Status.IN_TRANSIT
    transfer.save()
    create_outbox_event(
        event_type="transfer.shipped",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": transfer.destination_store.region.code},
        entity_version=4,
    )
    create_audit_log(
        action="transfer.shipped",
        instance=transfer,
        before=before,
        after=serialize_instance(transfer),
    )
    return transfer


@transaction.atomic
def deliver_transfer(transfer):
    transfer = _lock_transfer(transfer)
    if transfer.status != SupplyTransfer.Status.IN_TRANSIT:
        raise InventoryServiceError("Only in-transit transfers can be delivered.")
    before = serialize_instance(transfer)
    transfer.status = SupplyTransfer.Status.DELIVERED
    transfer.delivered_at = timezone.now()
    transfer.save()
    create_outbox_event(
        event_type="transfer.delivered",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": transfer.destination_store.region.code},
        entity_version=5,
    )
    create_audit_log(
        action="transfer.delivered",
        instance=transfer,
        before=before,
        after=serialize_instance(transfer),
    )
    return transfer


@transaction.atomic
def receive_transfer(transfer, *, actor=None):
    transfer = _lock_transfer(transfer)
    if transfer.status != SupplyTransfer.Status.DELIVERED:
        raise InventoryServiceError("Only delivered transfers can be received.")
    for line_item in _locked_transfer_line_items(transfer):
        quantity = line_item.quantity_received or line_item.quantity_approved
        if quantity <= 0:
            raise InventoryServiceError(
                "Received transfer quantities must be positive."
            )
        if quantity > line_item.quantity_approved:
            raise InventoryServiceError(
                "Received quantity cannot exceed approved transfer quantity."
            )
        balance = get_store_balance(
            transfer.destination_store, line_item.inventory_item
        )
        apply_balance_change(balance, on_hand_delta=quantity)
        evaluate_restock_alert(balance)

    before = serialize_instance(transfer)
    transfer.status = SupplyTransfer.Status.RECEIVED
    transfer.received_at = timezone.now()
    transfer.save()
    create_outbox_event(
        event_type="transfer.received",
        instance=transfer,
        payload={"status": transfer.status},
        source_scope={"region_code": transfer.destination_store.region.code},
        entity_version=6,
    )
    create_audit_log(
        actor=actor,
        action="transfer.received",
        instance=transfer,
        before=before,
        after=serialize_instance(transfer),
    )
    return transfer


def progress_transfer(transfer, *, actor, action):
    if action == "approve":
        return approve_transfer(transfer, approver=actor)
    if action == "reserve":
        if not user_can_progress_transfer(actor, transfer):
            raise InventoryServiceError("You cannot reserve this transfer.")
        return reserve_transfer_inventory(transfer)
    if action == "ship":
        if not user_can_progress_transfer(actor, transfer):
            raise InventoryServiceError("You cannot ship this transfer.")
        return ship_transfer(transfer)
    if action == "deliver":
        if not user_can_progress_transfer(actor, transfer):
            raise InventoryServiceError("You cannot deliver this transfer.")
        return deliver_transfer(transfer)
    if action == "receive":
        if not user_can_receive_transfer(actor, transfer):
            raise InventoryServiceError("You cannot receive this transfer.")
        return receive_transfer(transfer, actor=actor)
    raise InventoryServiceError("Unsupported transfer action.")


def approve_supply_schedule(schedule, *, approver):
    if approver.role not in {
        approver.Role.LOGISTICS_MANAGER,
        approver.Role.SUPER_ADMIN,
    }:
        raise InventoryServiceError(
            "Only logistics managers or super admins can approve supply schedules."
        )
    schedule.status = SupplySchedule.Status.APPROVED
    schedule.approved_by = approver
    schedule.save()
    return schedule


@transaction.atomic
def create_supplier_replenishment_order(
    *,
    actor,
    supplier,
    store,
    inventory_item,
    quantity_requested,
    expected_delivery_date=None,
    unit_cost=None,
    notes="",
):
    if not user_can_manage_supplier_order(actor, store):
        raise InventoryServiceError("You cannot order supplies for that store.")
    if supplier.service_region_id and supplier.service_region_id != store.region_id:
        raise InventoryServiceError(
            "Supplier must service the destination store region."
        )

    quantity_requested = normalize_bulk_order_quantity(
        inventory_item, quantity_requested
    )
    replenishment = SupplierReplenishment.objects.create(
        supplier=supplier,
        store=store,
        inventory_item=inventory_item,
        quantity_requested=quantity_requested,
        quantity_received=Decimal("0.00"),
        requested_by=actor,
        ordered_at=timezone.now(),
        expected_delivery_date=expected_delivery_date,
        recorded_by=actor,
        unit_cost=unit_cost,
        status=SupplierReplenishment.Status.ORDERED,
        notes=notes,
    )
    create_outbox_event(
        event_type="supplier_replenishment.ordered",
        instance=replenishment,
        payload={
            "status": replenishment.status,
            "quantity_requested": str(quantity_requested),
        },
        source_scope={"region_code": store.region.code},
    )
    create_audit_log(
        actor=actor,
        action="supplier_replenishment.ordered",
        instance=replenishment,
        after=serialize_instance(replenishment),
    )
    return replenishment


@transaction.atomic
def receive_supplier_replenishment(
    replenishment,
    *,
    actor,
    quantity_received=None,
    unit_cost=None,
):
    if not user_can_manage_supplier_order(actor, replenishment.store):
        raise InventoryServiceError("You cannot receive supplies for that store.")
    if replenishment.status != SupplierReplenishment.Status.ORDERED:
        raise InventoryServiceError(
            "Only ordered supplier replenishments can be received."
        )

    quantity_received = _as_decimal(
        quantity_received or replenishment.quantity_requested
    )
    if quantity_received <= 0:
        raise InventoryServiceError("Received quantity must be positive.")

    balance = get_store_balance(replenishment.store, replenishment.inventory_item)
    apply_balance_change(balance, on_hand_delta=quantity_received)
    evaluate_restock_alert(balance)

    before = serialize_instance(replenishment)
    replenishment.quantity_received = quantity_received
    replenishment.received_at = timezone.now()
    replenishment.recorded_by = actor
    replenishment.status = SupplierReplenishment.Status.RECEIVED
    if unit_cost is not None:
        replenishment.unit_cost = unit_cost
    replenishment.save()
    create_outbox_event(
        event_type="supplier_replenishment.received",
        instance=replenishment,
        payload={
            "status": replenishment.status,
            "quantity_received": str(quantity_received),
        },
        source_scope={"region_code": replenishment.store.region.code},
    )
    create_audit_log(
        actor=actor,
        action="supplier_replenishment.received",
        instance=replenishment,
        before=before,
        after=serialize_instance(replenishment),
    )
    return replenishment


@transaction.atomic
def cancel_supplier_replenishment(replenishment, *, actor):
    if not user_can_manage_supplier_order(actor, replenishment.store):
        raise InventoryServiceError("You cannot cancel supplies for that store.")
    if replenishment.status != SupplierReplenishment.Status.ORDERED:
        raise InventoryServiceError(
            "Only ordered supplier replenishments can be canceled."
        )

    before = serialize_instance(replenishment)
    replenishment.status = SupplierReplenishment.Status.CANCELED
    replenishment.save()
    create_outbox_event(
        event_type="supplier_replenishment.canceled",
        instance=replenishment,
        payload={"status": replenishment.status},
        source_scope={"region_code": replenishment.store.region.code},
    )
    create_audit_log(
        actor=actor,
        action="supplier_replenishment.canceled",
        instance=replenishment,
        before=before,
        after=serialize_instance(replenishment),
    )
    return replenishment


def draft_supply_schedule_from_usage(
    *, store, inventory_item, quantity_used, source_type, source_reference
):
    recommended_quantity = recommended_bulk_quantity(inventory_item, quantity_used)
    recommended_frequency_days = 21 if inventory_item.is_perishable else 30
    schedule, _ = SupplySchedule.objects.update_or_create(
        store=store,
        inventory_item=inventory_item,
        defaults={
            "recommended_source_type": source_type,
            "recommended_source_reference": source_reference,
            "recommended_quantity": recommended_quantity,
            "recommended_frequency_days": recommended_frequency_days,
            "created_by_ai": True,
            "status": SupplySchedule.Status.DRAFT,
            "approved_by": None,
        },
    )
    return schedule


def adjust_store_inventory(*, balance, delta, actor=None, reason=""):
    before = serialize_instance(balance)
    apply_balance_change(balance, on_hand_delta=_as_decimal(delta))
    evaluate_restock_alert(balance)
    create_audit_log(
        actor=actor,
        action="inventory.adjusted",
        instance=balance,
        before=before,
        after=serialize_instance(balance),
    )
    return balance
