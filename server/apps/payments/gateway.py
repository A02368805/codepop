from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


class PaymentMode:
    MOCK = "mock"
    STRIPE = "stripe"


class CheckoutFlow:
    HOSTED = "hosted"
    ELEMENTS = "elements"


@dataclass(frozen=True)
class CheckoutSessionResult:
    checkout_url: str
    checkout_session_id: str
    payment_intent_id: str


@dataclass(frozen=True)
class PaymentIntentResult:
    payment_intent_id: str
    client_secret: str


def get_payment_mode():
    configured_mode = getattr(settings, "PAYMENT_MODE", PaymentMode.MOCK).lower()
    if configured_mode == PaymentMode.STRIPE and getattr(
        settings, "STRIPE_SECRET_KEY", ""
    ):
        return PaymentMode.STRIPE
    return PaymentMode.MOCK


def stripe_is_configured():
    return get_payment_mode() == PaymentMode.STRIPE


def get_checkout_flow():
    configured_flow = getattr(settings, "PAYMENT_CHECKOUT_FLOW", CheckoutFlow.HOSTED)
    configured_flow = str(configured_flow or CheckoutFlow.HOSTED).strip().lower()
    if configured_flow == CheckoutFlow.ELEMENTS:
        return CheckoutFlow.ELEMENTS
    return CheckoutFlow.HOSTED


def _import_stripe():
    try:
        import stripe  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Stripe support requires the 'stripe' package to be installed."
        ) from exc
    return stripe


def _client():
    stripe = _import_stripe()
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_stripe_checkout_session(*, order, success_url, cancel_url):
    client = _client()
    idempotency_key = f"checkout:{order.public_order_code}"
    session = client.checkout.Session.create(
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": str(order.pk), "order_code": order.public_order_code},
        line_items=[
            {
                "quantity": item.quantity,
                "price_data": {
                    "currency": order.currency.lower(),
                    "unit_amount": int((item.line_total / item.quantity) * 100),
                    "product_data": {
                        "name": item.display_name_snapshot,
                        "description": item.size_snapshot.title(),
                    },
                },
            }
            for item in order.items.all()
        ],
        idempotency_key=idempotency_key,
    )
    return CheckoutSessionResult(
        checkout_url=session.url,
        checkout_session_id=session.id,
        payment_intent_id=getattr(session, "payment_intent", "") or "",
    )


def create_stripe_payment_intent(*, order):
    client = _client()
    idempotency_key = f"payment_intent:{order.public_order_code}"
    payment_intent = client.PaymentIntent.create(
        amount=int(order.total_amount * 100),
        currency=order.currency.lower(),
        metadata={"order_id": str(order.pk), "order_code": order.public_order_code},
        automatic_payment_methods={"enabled": True},
        idempotency_key=idempotency_key,
    )
    return PaymentIntentResult(
        payment_intent_id=payment_intent.id,
        client_secret=getattr(payment_intent, "client_secret", "") or "",
    )


def retrieve_stripe_payment_intent(payment_intent_id):
    payment_intent = _client().PaymentIntent.retrieve(payment_intent_id)
    return PaymentIntentResult(
        payment_intent_id=getattr(payment_intent, "id", "") or payment_intent_id,
        client_secret=getattr(payment_intent, "client_secret", "") or "",
    )


def retrieve_checkout_session(session_id):
    return _client().checkout.Session.retrieve(session_id)


def construct_webhook_event(*, payload, signature):
    return _client().Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
