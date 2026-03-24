from datetime import date

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from apps.orders.models import Order
from apps.orders.selectors import authorize_guest_lookup
from apps.stores.selectors import scoped_region_store_options, stores_visible_to_user
from apps.users.models import User
from apps.users.permissions import RoleRequiredMixin

from .gateway import PaymentMode, construct_webhook_event, get_payment_mode, stripe_is_configured
from .models import PaymentTransaction, RevenueLedgerEntry
from .services import PaymentGatewayError, finalize_stripe_checkout, record_payment_failure, record_refund


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class PaymentWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "payments/index.html"
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.ADMIN,
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
        search = self.request.GET.get("q", "").strip()
        date_from = _parse_date(self.request.GET.get("date_from", "").strip())
        date_to = _parse_date(self.request.GET.get("date_to", "").strip())
        transactions = PaymentTransaction.objects.filter(store__in=visible_stores).select_related("order", "store")
        if search:
            transactions = transactions.filter(order__public_order_code__icontains=search)
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
        if order.order_type == Order.OrderType.GUEST and hasattr(order, "guest_contact"):
            authorize_guest_lookup(request.session, order.guest_contact.lookup_code)
        messages.success(request, "Payment completed successfully.")
        return redirect("orders:confirmation", order_code=order.public_order_code)


class CheckoutCancelView(View):
    def get(self, request, *args, **kwargs):
        order_code = request.GET.get("order_code", "").strip()
        order = get_object_or_404(Order, public_order_code=order_code)
        if order.order_type == Order.OrderType.GUEST and hasattr(order, "guest_contact"):
            authorize_guest_lookup(request.session, order.guest_contact.lookup_code)
        if order.status == Order.Status.PAYMENT_PENDING:
            record_payment_failure(
                order,
                actor=request.user if request.user.is_authenticated else None,
                reason="Stripe checkout was canceled.",
            )
        messages.warning(request, "Checkout was canceled.")
        return redirect("orders:detail", order_code=order.public_order_code)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        signature = request.headers.get("Stripe-Signature", "")
        try:
            event = construct_webhook_event(payload=request.body, signature=signature)
        except Exception:
            return HttpResponseBadRequest("Invalid Stripe webhook signature.")

        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            session_id = data_object.get("id", "")
            if order_code and session_id:
                finalize_stripe_checkout(order_code=order_code, session_id=session_id)
        elif event_type == "checkout.session.expired":
            order_code = data_object.get("metadata", {}).get("order_code", "")
            if order_code:
                order = Order.objects.filter(public_order_code=order_code).first()
                if order:
                    record_payment_failure(order, reason="Stripe checkout session expired.")
        elif event_type == "charge.refunded":
            payment_intent_id = data_object.get("payment_intent", "")
            payment = PaymentTransaction.objects.filter(
                stripe_payment_intent_id=payment_intent_id
            ).select_related("order").first()
            if payment:
                record_refund(payment.order, notes="Stripe webhook refund confirmation.")

        return HttpResponse(status=200)
