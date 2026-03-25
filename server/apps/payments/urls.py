from django.urls import path

from .views import (
    CheckoutCancelView,
    PaymentIntentCreateView,
    CheckoutSuccessView,
    PaymentWorkspaceView,
    StripeWebhookView,
)

app_name = "payments"

urlpatterns = [
    path("", PaymentWorkspaceView.as_view(), name="index"),
    path("payment-intent/", PaymentIntentCreateView.as_view(), name="payment-intent"),
    path("checkout/success/", CheckoutSuccessView.as_view(), name="checkout-success"),
    path("checkout/cancel/", CheckoutCancelView.as_view(), name="checkout-cancel"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
