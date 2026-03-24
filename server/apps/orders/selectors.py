from django.db.models import Count, Sum

from apps.stores.selectors import stores_visible_to_user
from apps.users.models import User
from apps.users.permissions import user_can_manage_store, user_has_global_access

from .models import Order


GUEST_LOOKUP_SESSION_KEY = "codepop_guest_lookup_codes"


def account_order_history(user):
    return (
        Order.objects.filter(customer=user)
        .select_related("store", "payment_transaction")
        .prefetch_related("items")
        .order_by("-created_at")
    )


def staff_order_queue(user):
    visible_stores = stores_visible_to_user(user)
    return (
        Order.objects.filter(store__in=visible_stores)
        .select_related("store", "customer", "payment_transaction")
        .prefetch_related("items")
        .exclude(status__in=[Order.Status.REFUNDED, Order.Status.CANCELED, Order.Status.PICKED_UP])
        .order_by("pickup_time_requested", "-created_at")
    )


def authorize_guest_lookup(session, lookup_code):
    lookup_codes = set(session.get(GUEST_LOOKUP_SESSION_KEY, []))
    lookup_codes.add(lookup_code)
    session[GUEST_LOOKUP_SESSION_KEY] = sorted(lookup_codes)
    session.modified = True


def session_can_view_guest_order(session, order):
    if not hasattr(order, "guest_contact"):
        return False
    lookup_codes = set(session.get(GUEST_LOOKUP_SESSION_KEY, []))
    return order.guest_contact.lookup_code in lookup_codes


def user_can_view_order(user, order, *, session=None):
    if order.order_type == Order.OrderType.GUEST and session and session_can_view_guest_order(session, order):
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    if user.role == User.Role.ACCOUNT_USER:
        return order.customer_id == user.id
    if user.role in {User.Role.MANAGER, User.Role.ADMIN}:
        return user_can_manage_store(user, order.store)
    return False


def user_can_transition_order(user, order):
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    return user.role == User.Role.MANAGER and user_can_manage_store(user, order.store)


def payment_summary_for_stores(stores):
    orders = Order.objects.filter(store__in=stores)
    return orders.aggregate(
        total_revenue=Sum("revenue_entries__net_amount"),
        total_orders=Count("id"),
    )
