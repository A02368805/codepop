from __future__ import annotations

from decimal import Decimal

from apps.inventory.services import InventoryServiceError
from apps.orders.models import Order
from apps.orders.services import ensure_refund_allowed, transition_order_status
from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance
from core.exceptions import ServiceError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .gateway import (
    CheckoutFlow,
    PaymentMode,
    create_stripe_checkout_session,
    create_stripe_payment_intent,
    get_checkout_flow,
    get_payment_mode,
    retrieve_checkout_session,
    retrieve_stripe_payment_intent,
)
from .models import PaymentTransaction, RevenueLedgerEntry


class PaymentServiceError(ServiceError):
    pass


class PaymentGatewayError(PaymentServiceError):
    pass


def create_payment_intent_for_order(order, *, actor=None):
    if order.status not in {
        Order.Status.PRICING_VALIDATED,
        Order.Status.PAYMENT_PENDING,
    }:
        raise PaymentServiceError(
            "Payment intent can only be created for pricing-validated or pending-payment orders."
        )

    mode = get_payment_mode()
    if mode == PaymentMode.MOCK:
        mock_client_secret = f"mock_client_secret_{order.public_order_code.lower()}"
        record_payment_pending(
            order,
            payment_intent_id=mock_client_secret,
            provider=PaymentTransaction.Provider.MOCK,
        )
        return {
            "provider": PaymentTransaction.Provider.MOCK,
            "payment_intent_id": mock_client_secret,
            "client_secret": mock_client_secret,
        }

    existing = getattr(order, "payment_transaction", None)
    if (
        existing
        and existing.provider == PaymentTransaction.Provider.STRIPE
        and existing.status == PaymentTransaction.Status.PENDING
        and existing.stripe_payment_intent_id
    ):
        try:
            existing_intent = retrieve_stripe_payment_intent(
                existing.stripe_payment_intent_id
            )
            if existing_intent.client_secret:
                return {
                    "provider": PaymentTransaction.Provider.STRIPE,
                    "payment_intent_id": existing_intent.payment_intent_id,
                    "client_secret": existing_intent.client_secret,
                }
        except Exception:
            pass

    intent = create_stripe_payment_intent(order=order)
    record_payment_pending(
        order,
        payment_intent_id=intent.payment_intent_id,
        provider=PaymentTransaction.Provider.STRIPE,
    )
    return {
        "provider": PaymentTransaction.Provider.STRIPE,
        "payment_intent_id": intent.payment_intent_id,
        "client_secret": intent.client_secret,
    }


@transaction.atomic
def record_payment_pending(
    order,
    *,
    payment_intent_id="",
    amount_authorized=None,
    provider=PaymentTransaction.Provider.STRIPE,
    checkout_session_id="",
):
    amount_authorized = amount_authorized or order.total_amount
    payment, _ = PaymentTransaction.objects.update_or_create(
        order=order,
        defaults={
            "store": order.store,
            "provider": provider,
            "status": PaymentTransaction.Status.PENDING,
            "amount_authorized": amount_authorized,
            "stripe_payment_intent_id": payment_intent_id,
            "checkout_session_id": checkout_session_id,
            "failure_reason": "",
        },
    )
    if order.status == Order.Status.PRICING_VALIDATED:
        transition_order_status(order, Order.Status.PAYMENT_PENDING)
    return payment


@transaction.atomic
def record_payment_success(
    order,
    *,
    payment_intent_id="",
    captured_amount=None,
    actor=None,
    provider=PaymentTransaction.Provider.STRIPE,
    checkout_session_id="",
):
    captured_amount = captured_amount or order.total_amount
    payment, _ = PaymentTransaction.objects.update_or_create(
        order=order,
        defaults={
            "store": order.store,
            "provider": provider,
            "status": PaymentTransaction.Status.SUCCEEDED,
            "amount_authorized": captured_amount,
            "amount_captured": captured_amount,
            "stripe_payment_intent_id": payment_intent_id,
            "checkout_session_id": checkout_session_id,
            "captured_at": timezone.now(),
            "failure_reason": "",
        },
    )
    if order.status == Order.Status.PAYMENT_PENDING:
        transition_order_status(order, Order.Status.PAID, actor=actor)

    RevenueLedgerEntry.objects.get_or_create(
        store=order.store,
        order=order,
        entry_type=RevenueLedgerEntry.EntryType.SALE,
        defaults={
            "gross_amount": captured_amount,
            "net_amount": captured_amount,
            "notes": "Order payment captured.",
        },
    )
    create_audit_log(
        actor=actor,
        action="payment.succeeded",
        instance=payment,
        after=serialize_instance(payment),
    )
    return payment


@transaction.atomic
def record_payment_failure(
    order, *, actor=None, reason="", payment_intent_id="", checkout_session_id=""
):
    before = (
        serialize_instance(order.payment_transaction)
        if hasattr(order, "payment_transaction")
        else {}
    )
    payment, _ = PaymentTransaction.objects.update_or_create(
        order=order,
        defaults={
            "store": order.store,
            "provider": (
                PaymentTransaction.Provider.STRIPE
                if get_payment_mode() == PaymentMode.STRIPE
                else PaymentTransaction.Provider.MOCK
            ),
            "status": PaymentTransaction.Status.FAILED,
            "amount_authorized": order.total_amount,
            "stripe_payment_intent_id": payment_intent_id,
            "checkout_session_id": checkout_session_id,
            "failure_reason": reason,
        },
    )
    if order.status == Order.Status.PAYMENT_PENDING:
        transition_order_status(
            order,
            Order.Status.CANCELED,
            actor=actor,
            reason=reason or "Payment failed.",
        )
    create_outbox_event(
        event_type="order.failed",
        instance=order,
        payload={"reason": reason or "Payment failed."},
        source_scope={
            "store_id": str(order.store_id),
            "region_code": order.store.region.code,
        },
    )
    create_audit_log(
        actor=actor,
        action="payment.failed",
        instance=payment,
        before=before,
        after=serialize_instance(payment),
    )
    return payment


@transaction.atomic
def complete_checkout_payment(
    order,
    *,
    actor=None,
    payment_intent_id="",
    provider=PaymentTransaction.Provider.STRIPE,
    checkout_session_id="",
):
    payment = record_payment_success(
        order,
        payment_intent_id=payment_intent_id,
        actor=actor,
        provider=provider,
        checkout_session_id=checkout_session_id,
    )
    order.refresh_from_db()
    if order.status == Order.Status.PAID:
        transition_order_status(order, Order.Status.QUEUED, actor=actor)
    return payment


def initialize_order_checkout(order, *, request, actor=None):
    mode = get_payment_mode()
    if mode == PaymentMode.MOCK:
        mock_reference = f"mock_{order.public_order_code.lower()}"
        record_payment_pending(
            order,
            payment_intent_id=mock_reference,
            provider=PaymentTransaction.Provider.MOCK,
        )
        try:
            complete_checkout_payment(
                order,
                actor=actor,
                payment_intent_id=mock_reference,
                provider=PaymentTransaction.Provider.MOCK,
            )
        except InventoryServiceError as exc:
            order.refresh_from_db()
            record_payment_failure(
                order,
                actor=actor,
                reason=str(exc),
                payment_intent_id=mock_reference,
            )
            raise PaymentGatewayError(str(exc)) from exc
        return {
            "mode": PaymentMode.MOCK,
            "redirect_url": reverse(
                "orders:confirmation", args=[order.public_order_code]
            ),
            "message": "Demo payment mode completed the order instantly.",
        }

    checkout_flow = get_checkout_flow()
    if checkout_flow == CheckoutFlow.ELEMENTS:
        return {
            "mode": PaymentMode.STRIPE,
            "redirect_url": reverse("orders:detail", args=[order.public_order_code]),
            "message": "Enter your card details to complete payment.",
        }

    if not getattr(request, "build_absolute_uri", None):
        raise PaymentGatewayError(
            "A request object is required for Stripe checkout initialization."
        )

    success_url = (
        request.build_absolute_uri(reverse("payments:checkout-success"))
        + f"?order_code={order.public_order_code}&session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("payments:checkout-cancel"))
        + f"?order_code={order.public_order_code}"
    )
    session = create_stripe_checkout_session(
        order=order,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    record_payment_pending(
        order,
        payment_intent_id=session.payment_intent_id or session.checkout_session_id,
        provider=PaymentTransaction.Provider.STRIPE,
        checkout_session_id=session.checkout_session_id,
    )
    return {
        "mode": PaymentMode.STRIPE,
        "redirect_url": session.checkout_url,
        "message": "Redirecting to Stripe checkout.",
    }


def finalize_stripe_checkout(*, order_code, session_id, actor=None):
    session = retrieve_checkout_session(session_id)
    order = Order.objects.select_related("payment_transaction", "store").get(
        public_order_code=order_code
    )
    if order.status in {
        Order.Status.QUEUED,
        Order.Status.PREPARING,
        Order.Status.READY,
        Order.Status.PICKED_UP,
    }:
        payment = getattr(order, "payment_transaction", None)
        if payment:
            payment.last_webhook_at = timezone.now()
            payment.save(update_fields=["last_webhook_at"])
        return order
    if session.payment_status != "paid":
        raise PaymentGatewayError("Stripe checkout has not completed payment yet.")
    try:
        complete_checkout_payment(
            order,
            actor=actor,
            payment_intent_id=getattr(session, "payment_intent", "") or session.id,
            provider=PaymentTransaction.Provider.STRIPE,
            checkout_session_id=session.id,
        )
    except InventoryServiceError as exc:
        raise PaymentGatewayError(str(exc)) from exc
    payment = order.payment_transaction
    payment.last_webhook_at = timezone.now()
    payment.save(update_fields=["last_webhook_at"])
    return order


def finalize_stripe_payment_intent(*, order_code, payment_intent_id, actor=None):
    order = Order.objects.select_related("store").get(public_order_code=order_code)
    if order.status in {
        Order.Status.QUEUED,
        Order.Status.PREPARING,
        Order.Status.READY,
        Order.Status.PICKED_UP,
    }:
        payment = getattr(order, "payment_transaction", None)
        if payment:
            payment.last_webhook_at = timezone.now()
            payment.save(update_fields=["last_webhook_at"])
        return order

    try:
        complete_checkout_payment(
            order,
            actor=actor,
            payment_intent_id=payment_intent_id,
            provider=PaymentTransaction.Provider.STRIPE,
        )
    except InventoryServiceError as exc:
        raise PaymentGatewayError(str(exc)) from exc

    payment = order.payment_transaction
    payment.last_webhook_at = timezone.now()
    payment.save(update_fields=["last_webhook_at"])
    return order


@transaction.atomic
def record_refund(order, *, actor=None, amount=None, notes=""):
    ensure_refund_allowed(order, actor=actor)
    payment = order.payment_transaction
    if order.status in {
        Order.Status.QUEUED,
        Order.Status.PREPARING,
        Order.Status.READY,
    }:
        from apps.inventory.services import reverse_order_inventory

        reverse_order_inventory(order)
    refund_amount = Decimal(
        str(amount or payment.amount_captured or order.total_amount)
    )
    transition_order_status(
        order, Order.Status.REFUND_PENDING, actor=actor, reason=notes
    )

    payment.amount_refunded += refund_amount
    payment.status = (
        PaymentTransaction.Status.REFUNDED
        if payment.amount_refunded >= payment.amount_captured
        else PaymentTransaction.Status.PARTIALLY_REFUNDED
    )
    payment.save()
    RevenueLedgerEntry.objects.create(
        store=order.store,
        order=order,
        entry_type=RevenueLedgerEntry.EntryType.REFUND,
        gross_amount=refund_amount,
        net_amount=-refund_amount,
        notes=notes or "Refund issued.",
    )
    transition_order_status(order, Order.Status.REFUNDED, actor=actor, reason=notes)
    create_audit_log(
        actor=actor,
        action="payment.refunded",
        instance=payment,
        after=serialize_instance(payment),
    )
    return payment
