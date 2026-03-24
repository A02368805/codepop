from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import secrets

from django.db import transaction
from django.utils import timezone

from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance

from .models import GuestOrderContact, Order, OrderItem


DEFAULT_TAX_RATE = Decimal("0.0725")


class OrderServiceError(Exception):
    pass


class PricingValidationError(OrderServiceError):
    pass


class OrderStateTransitionError(OrderServiceError):
    pass


class RefundEligibilityError(OrderServiceError):
    pass


ALLOWED_ORDER_TRANSITIONS = {
    Order.Status.DRAFT: {Order.Status.PRICING_VALIDATED, Order.Status.CANCELED},
    Order.Status.PRICING_VALIDATED: {Order.Status.PAYMENT_PENDING, Order.Status.CANCELED},
    Order.Status.PAYMENT_PENDING: {Order.Status.PAID, Order.Status.CANCELED},
    Order.Status.PAID: {
        Order.Status.QUEUED,
        Order.Status.REFUND_PENDING,
        Order.Status.CANCELED,
    },
    Order.Status.QUEUED: {
        Order.Status.PREPARING,
        Order.Status.REFUND_PENDING,
        Order.Status.CANCELED,
    },
    Order.Status.PREPARING: {Order.Status.READY, Order.Status.REFUND_PENDING},
    Order.Status.READY: {Order.Status.PICKED_UP, Order.Status.EXPIRED},
    Order.Status.REFUND_PENDING: {Order.Status.REFUNDED},
}


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_public_order_code(store) -> str:
    return f"FS-{store.region.code}-{store.store_code}-{uuid.uuid4().hex[:6].upper()}"


def generate_guest_lookup_code() -> str:
    return f"GST-{uuid.uuid4().hex[:8].upper()}"


def assign_pickup_locker(order):
    if order.locker_number and order.locker_code:
        return order
    active_numbers = set(
        Order.objects.filter(
            store=order.store,
            status=Order.Status.READY,
        )
        .exclude(pk=order.pk)
        .exclude(locker_number="")
        .values_list("locker_number", flat=True)
    )
    for locker_number in range(1, 25):
        locker_label = f"L{locker_number:02d}"
        if locker_label not in active_numbers:
            order.locker_number = locker_label
            break
    if not order.locker_number:
        order.locker_number = f"L{(order.store.orders.count() % 24) + 1:02d}"
    order.locker_code = f"{secrets.randbelow(90) + 10}-{secrets.randbelow(900) + 100}"
    return order


def validate_pricing(*, store, items, tax_rate=DEFAULT_TAX_RATE):
    if not items:
        raise PricingValidationError("An order must contain at least one item.")

    normalized_items = []
    subtotal = Decimal("0.00")

    for item in items:
        display_name = item.get("display_name") or item.get("name")
        if not display_name:
            raise PricingValidationError("Each item requires a display name.")

        quantity = int(item.get("quantity", 1))
        if quantity <= 0:
            raise PricingValidationError("Item quantity must be positive.")

        base_price = _money(item.get("base_price", 0))
        customizations = item.get("customizations") or item.get("customizations_json") or {}
        extras_total = _money(item.get("extras_total", customizations.get("extras_total", 0)))
        line_total = _money((base_price + extras_total) * quantity)
        subtotal += line_total

        normalized_items.append(
            {
                "template_reference_id": item.get("template_reference_id"),
                "display_name_snapshot": display_name,
                "size_snapshot": item.get("size") or item.get("size_snapshot") or "medium",
                "base_price_snapshot": base_price,
                "customizations_json": customizations,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    tax_amount = _money(subtotal * tax_rate)
    total_amount = subtotal + tax_amount

    return {
        "store_id": store.pk,
        "normalized_items": normalized_items,
        "subtotal_amount": subtotal,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "currency": "USD",
    }


@transaction.atomic
def create_order(
    *,
    store,
    items,
    customer=None,
    guest_contact=None,
    pickup_time_requested=None,
    notes="",
    actor=None,
):
    pricing = validate_pricing(store=store, items=items)
    order = Order.objects.create(
        public_order_code=generate_public_order_code(store),
        store=store,
        customer=customer,
        order_type=Order.OrderType.ACCOUNT if customer else Order.OrderType.GUEST,
        status=Order.Status.PRICING_VALIDATED,
        pickup_time_requested=pickup_time_requested,
        subtotal_amount=pricing["subtotal_amount"],
        tax_amount=pricing["tax_amount"],
        total_amount=pricing["total_amount"],
        currency=pricing["currency"],
        notes=notes,
    )

    for item in pricing["normalized_items"]:
        OrderItem.objects.create(order=order, **item)

    if guest_contact and not customer:
        GuestOrderContact.objects.create(
            order=order,
            display_name=guest_contact.get("display_name", ""),
            email=guest_contact.get("email", ""),
            phone_number=guest_contact.get("phone_number", ""),
            lookup_code=guest_contact.get("lookup_code", generate_guest_lookup_code()),
            expires_at=guest_contact.get("expires_at"),
        )

    create_outbox_event(
        event_type="order.created",
        instance=order,
        payload={"status": order.status, "store_id": str(order.store_id)},
        source_scope={"store_id": str(order.store_id), "region_code": order.store.region.code},
    )

    create_audit_log(
        actor=actor,
        action="order.created",
        instance=order,
        after=serialize_instance(order),
    )
    return order


@transaction.atomic
def transition_order_status(order, new_status, *, actor=None, reason=""):
    allowed = ALLOWED_ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise OrderStateTransitionError(
            f"Cannot transition order from {order.status} to {new_status}."
        )

    before = serialize_instance(order)
    now = timezone.now()

    if new_status == Order.Status.PAID and order.placed_at is None:
        order.placed_at = now
    if new_status == Order.Status.QUEUED and order.queued_at is None:
        order.queued_at = now
        from apps.inventory.services import reserve_order_inventory

        reserve_order_inventory(order)
    if new_status == Order.Status.PREPARING and order.preparing_at is None:
        order.preparing_at = now
    if new_status == Order.Status.READY and order.ready_at is None:
        order.ready_at = now
        order.expires_at = now + timedelta(hours=1)
        assign_pickup_locker(order)
    if new_status == Order.Status.PICKED_UP and order.picked_up_at is None:
        order.picked_up_at = now
    if new_status == Order.Status.CANCELED:
        order.cancel_reason = reason or order.cancel_reason
    if new_status == Order.Status.REFUND_PENDING:
        order.refund_status = Order.RefundStatus.REQUESTED
    if new_status == Order.Status.REFUNDED:
        order.refund_status = Order.RefundStatus.REFUNDED

    order.status = new_status
    order.save()

    create_outbox_event(
        event_type=f"order.{new_status}",
        instance=order,
        payload={"status": new_status, "store_id": str(order.store_id)},
        source_scope={"store_id": str(order.store_id), "region_code": order.store.region.code},
    )
    create_audit_log(
        actor=actor,
        action=f"order.transition.{new_status}",
        instance=order,
        before=before,
        after=serialize_instance(order),
    )
    if new_status == Order.Status.QUEUED and order.customer_id:
        from apps.analytics.tasks import refresh_account_recommendations

        transaction.on_commit(
            lambda: refresh_account_recommendations.delay(
                str(order.customer_id),
                reason="Based on your latest order",
            )
        )
    return order


def get_refund_eligibility(order, *, actor=None):
    privileged = bool(
        actor
        and getattr(actor, "is_authenticated", False)
        and actor.role in {actor.Role.ADMIN, actor.Role.SUPER_ADMIN}
    )

    if order.status in {Order.Status.PAID, Order.Status.QUEUED, Order.Status.PAYMENT_PENDING}:
        return True, "Refund is allowed before preparation begins."
    if order.status == Order.Status.PREPARING and privileged:
        return True, "Privileged override allows refund after preparation started."
    return False, "Refunds are disallowed after preparation begins unless a privileged override is used."


def ensure_refund_allowed(order, *, actor=None):
    allowed, reason = get_refund_eligibility(order, actor=actor)
    if not allowed:
        raise RefundEligibilityError(reason)
    return reason
