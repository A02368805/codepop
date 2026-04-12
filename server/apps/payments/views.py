from datetime import date

from apps.orders.models import Order
from apps.orders.selectors import authorize_guest_order_access, user_can_view_order
from apps.stores.selectors import scoped_region_store_options
from apps.users.permissions import RoleRequiredMixin, user_can_view_payments_workspace
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .gateway import (
    PaymentMode,
    construct_webhook_event,
    get_payment_mode,
    stripe_is_configured,
)
from .models import PaymentTransaction, PaymentWebhookEvent, RevenueLedgerEntry
from .services import (
    PaymentGatewayError,
    PaymentServiceError,
    create_payment_intent_for_order,
    finalize_stripe_checkout,
    finalize_stripe_payment_intent,
    record_payment_failure,
    record_refund,
)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class PaymentWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "payments/index.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not user_can_view_payments_workspace(request.user):
            raise PermissionDenied("You do not have access to this workspace.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = scoped_region_store_options(
            self.request.user,
            region_id=self.request.GET.get("region", "").strip(),
            store_id=self.request.GET.get("store", "").strip(),
        )
        visible_stores = scope["active_store_scope"]
        search = self.request.GET.get("q", "").strip()
        date_from = _parse_date(self.request.GET.get("date_from", "").strip())
        date_to = _parse_date(self.request.GET.get("date_to", "").strip())
        transactions = PaymentTransaction.objects.filter(
            store__in=visible_stores
        ).select_related("order", "store")
        if search:
            transactions = transactions.filter(
                order__public_order_code__icontains=search
            )
        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)
        revenue_entries = RevenueLedgerEntry.objects.filter(store__in=visible_stores)
        if date_from:
            revenue_entries = revenue_entries.filter(posted_at__date__gte=date_from)
        if date_to:
            revenue_entries = revenue_entries.filter(posted_at__date__lte=date_to)
        summary = revenue_entries.aggregate(
            gross=Sum("gross_amount"),
            net=Sum("net_amount"),
        )
        context.update(
            {
                "transactions": transactions.order_by("-created_at"),
                "gross_revenue": summary["gross"] or 0,
                "net_revenue": summary["net"] or 0,
                "search": search,
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
                "date_from": date_from.isoformat() if date_from else "",
                "date_to": date_to.isoformat() if date_to else "",
                "payment_mode": get_payment_mode(),
                "payment_mode_is_mock": get_payment_mode() == PaymentMode.MOCK,
                "stripe_ready": stripe_is_configured(),
            }
        )
        return context


class CheckoutSuccessView(View):
    def get(self, request, *args, **kwargs):
        order_code = request.GET.get("order_code", "").strip()
        session_id = request.GET.get("session_id", "").strip()
        if not order_code or not session_id:
            return HttpResponseBadRequest("Missing Stripe checkout identifiers.")
        try:
            order = finalize_stripe_checkout(
                order_code=order_code,
                session_id=session_id,
                actor=request.user if request.user.is_authenticated else None,
            )
        except PaymentGatewayError as exc:
            messages.error(request, str(exc))
            return redirect("orders:guest-lookup")
        if order.order_type == Order.OrderType.GUEST and hasattr(
            order, "guest_contact"
        ):
            authorize_guest_order_access(request.session, order)
        messages.success(request, "Payment completed successfully.")
        return redirect("orders:confirmation", order_code=order.public_order_code)


class CheckoutCancelView(View):
    def get(self, request, *args, **kwargs):
        order_code = request.GET.get("order_code", "").strip()
        order = get_object_or_404(Order, public_order_code=order_code)
        if order.order_type == Order.OrderType.GUEST and hasattr(
            order, "guest_contact"
        ):
            authorize_guest_order_access(request.session, order)
        if order.status == Order.Status.PAYMENT_PENDING:
            record_payment_failure(
                order,
                actor=request.user if request.user.is_authenticated else None,
                reason="Stripe checkout was canceled.",
            )
        messages.warning(request, "Checkout was canceled.")
        return redirect("orders:detail", order_code=order.public_order_code)


class PaymentIntentCreateView(View):
    def post(self, request, *args, **kwargs):
        order_code = request.POST.get("order_code", "").strip()
        if not order_code:
            return HttpResponseBadRequest("Missing order code.")

        order = get_object_or_404(
            Order.objects.select_related(
                "store", "payment_transaction"
            ).prefetch_related("items"),
            public_order_code=order_code,
        )
        if not user_can_view_order(request.user, order, session=request.session):
            return JsonResponse(
                {"error": "This order is outside your access scope."},
                status=403,
            )

        try:
            payload = create_payment_intent_for_order(
                order,
                actor=request.user if request.user.is_authenticated else None,
            )
        except PaymentServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse(payload)


class PaymentStatusView(View):
    def get(self, request, *args, **kwargs):
        order_code = request.GET.get("order_code", "").strip()
        if not order_code:
            return HttpResponseBadRequest("Missing order code.")

        order = get_object_or_404(
            Order.objects.select_related("payment_transaction"),
            public_order_code=order_code,
        )
        if not user_can_view_order(request.user, order, session=request.session):
            return JsonResponse(
                {"error": "This order is outside your access scope."},
                status=403,
            )

        payment = getattr(order, "payment_transaction", None)
        is_finalized = order.status in {
            Order.Status.PAID,
            Order.Status.QUEUED,
            Order.Status.PREPARING,
            Order.Status.READY,
            Order.Status.PICKED_UP,
        }
        return JsonResponse(
            {
                "order_code": order.public_order_code,
                "order_status": order.status,
                "payment_status": payment.status if payment else "none",
                "finalized": is_finalized,
                "redirect_url": (
                    reverse("orders:confirmation", args=[order.public_order_code])
                    if is_finalized
                    else ""
                ),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        signature = request.headers.get("Stripe-Signature", "")
        try:
            event = construct_webhook_event(payload=request.body, signature=signature)
        except Exception:
            return HttpResponseBadRequest("Invalid Stripe webhook signature.")

        event_id = event.get("id", "")
        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        if event_id:
            try:
                with transaction.atomic():
                    PaymentWebhookEvent.objects.create(
                        provider=PaymentWebhookEvent.Provider.STRIPE,
                        provider_event_id=event_id,
                        event_type=event_type,
                        payload=event,
                    )
            except IntegrityError:
                return HttpResponse(status=200)

        if event_type == "checkout.session.completed":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            session_id = data_object.get("id", "")
            if order_code and session_id:
                try:
                    finalize_stripe_checkout(
                        order_code=order_code, session_id=session_id
                    )
                except Exception:
                    return HttpResponse(status=200)
        elif event_type == "payment_intent.succeeded":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            payment_intent_id = data_object.get("id", "")
            if order_code and payment_intent_id:
                try:
                    finalize_stripe_payment_intent(
                        order_code=order_code,
                        payment_intent_id=payment_intent_id,
                    )
                except Exception:
                    return HttpResponse(status=200)
        elif event_type == "payment_intent.payment_failed":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            failure_message = (data_object.get("last_payment_error") or {}).get(
                "message"
            ) or "Stripe payment intent failed."
            if order_code:
                order = Order.objects.filter(public_order_code=order_code).first()
                if order and order.status == Order.Status.PAYMENT_PENDING:
                    record_payment_failure(order, reason=failure_message)
        elif event_type == "checkout.session.expired":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            if order_code:
                order = Order.objects.filter(public_order_code=order_code).first()
                if order:
                    record_payment_failure(
                        order, reason="Stripe checkout session expired."
                    )
        elif event_type == "charge.refunded":
            payment_intent_id = data_object.get("payment_intent", "")
            payment = (
                PaymentTransaction.objects.filter(
                    stripe_payment_intent_id=payment_intent_id
                )
                .select_related("order")
                .first()
            )
            if payment:
                if payment.status in {
                    PaymentTransaction.Status.REFUNDED,
                    PaymentTransaction.Status.PARTIALLY_REFUNDED,
                }:
                    return HttpResponse(status=200)
                try:
                    record_refund(
                        payment.order, notes="Stripe webhook refund confirmation."
                    )
                except Exception:
                    return HttpResponse(status=200)

        return HttpResponse(status=200)
