from django.db.models import F
from django.urls import reverse

from apps.imports.models import ImportJob
from apps.inventory.models import StoreInventoryBalance
from apps.maintenance.models import Machine, RepairAssignment
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction
from apps.stores.models import Region, Store
from apps.stores.selectors import regions_visible_to_user, stores_visible_to_user
from apps.supply_hubs.models import SupplyHub
from apps.sync.models import SyncOutboxEvent
from apps.users.models import User


ROLE_COPY = {
    User.Role.ACCOUNT_USER: {
        "title": "Customer Dashboard",
        "intro": "Your account workspace keeps ordering fast while still giving you favorites, recommendations, and order tracking.",
        "focus_items": [
            "Saved preferences and favorites",
            "Ready-for-pickup order tracking",
            "Preferred store and account settings",
        ],
    },
    User.Role.MANAGER: {
        "title": "Manager Dashboard",
        "intro": "Run a single store with queue controls, inventory visibility, revenue context, and machine watchlists.",
        "focus_items": [
            "Low-stock inventory watchlist",
            "Queued and preparing orders",
            "Machine warnings affecting store operations",
        ],
    },
    User.Role.ADMIN: {
        "title": "Admin Dashboard",
        "intro": "Admin screens stay people-and-governance focused rather than swallowing manager fulfillment work.",
        "focus_items": [
            "Store-scoped user management",
            "Role assignment auditing",
            "Operational alert visibility without direct ownership of fulfillment",
        ],
    },
    User.Role.LOGISTICS_MANAGER: {
        "title": "Logistics Dashboard",
        "intro": "The logistics workspace acts as an operations room for hubs, transfers, supply drafts, and imports.",
        "focus_items": [
            "Regional supply visibility",
            "Import queue health",
            "Transfer approval and future routing recommendations",
        ],
    },
    User.Role.REPAIR_STAFF: {
        "title": "Repair Dashboard",
        "intro": "Repair staff land on an urgency-first queue with assigned work, machine health context, and import history.",
        "focus_items": [
            "Open machine warnings and errors",
            "Assigned repair visits",
            "Upcoming service windows and CSV imports",
        ],
    },
    User.Role.SUPER_ADMIN: {
        "title": "Super Admin Dashboard",
        "intro": "System-wide oversight stays broad, while store and region ownership still belongs to the people closest to the work.",
        "focus_items": [
            "Cross-region health checks",
            "Global staffing and dashboard access visibility",
            "Operational analytics and sync health",
        ],
    },
}


def build_dashboard_payload(user, role):
    visible_stores = stores_visible_to_user(user)
    visible_regions = regions_visible_to_user(user)
    low_stock_count = StoreInventoryBalance.objects.filter(
        store__in=visible_stores, on_hand_quantity__lte=F("reorder_threshold")
    ).count()
    metrics = [
        {"label": "Stores in scope", "value": visible_stores.count(), "tone": "neutral"},
        {"label": "Regions in scope", "value": visible_regions.count(), "tone": "neutral"},
        {"label": "Low-stock balances", "value": low_stock_count, "tone": "warning"},
    ]

    if role == User.Role.ACCOUNT_USER:
        metrics = [
            {
                "label": "Preferred store",
                "value": user.preferred_store.name if user.preferred_store else "Not set",
                "tone": "neutral",
            },
            {
                "label": "Orders on record",
                "value": Order.objects.filter(customer=user).count(),
                "tone": "neutral",
            },
            {
                "label": "Unread updates",
                "value": Notification.objects.filter(user=user, is_read=False).count(),
                "tone": "info",
            },
        ]
    elif role == User.Role.MANAGER:
        metrics.append(
            {
                "label": "Orders awaiting action",
                "value": Order.objects.filter(
                    store__in=visible_stores,
                    status__in=[Order.Status.PAID, Order.Status.QUEUED, Order.Status.PREPARING, Order.Status.READY],
                ).count(),
                "tone": "info",
            }
        )
    elif role == User.Role.ADMIN:
        metrics.append(
            {
                "label": "Staff in scope",
                "value": User.objects.filter(store_assignments__store__in=visible_stores).distinct().count(),
                "tone": "info",
            }
        )
    elif role == User.Role.LOGISTICS_MANAGER:
        metrics.extend(
            [
                {
                    "label": "Supply hubs",
                    "value": SupplyHub.objects.filter(region__in=visible_regions).count(),
                    "tone": "neutral",
                },
                {
                    "label": "Pending sync events",
                    "value": SyncOutboxEvent.objects.filter(status=SyncOutboxEvent.Status.PENDING).count(),
                    "tone": "warning",
                },
            ]
        )
    elif role == User.Role.REPAIR_STAFF:
        metrics.extend(
            [
                {
                    "label": "Open assignments",
                    "value": RepairAssignment.objects.filter(
                        assigned_to=user,
                        status__in=[RepairAssignment.Status.SCHEDULED, RepairAssignment.Status.IN_PROGRESS],
                    ).count(),
                    "tone": "warning",
                },
                {
                    "label": "Machines in warning",
                    "value": Machine.objects.filter(
                        store__in=visible_stores,
                        current_status__in=[Machine.Status.WARNING, Machine.Status.ERROR],
                    ).count(),
                    "tone": "warning",
                },
            ]
        )
    elif role == User.Role.SUPER_ADMIN:
        metrics.extend(
            [
                {"label": "All stores", "value": Store.objects.count(), "tone": "neutral"},
                {
                    "label": "Recorded payments",
                    "value": PaymentTransaction.objects.exclude(status=PaymentTransaction.Status.FAILED).count(),
                    "tone": "info",
                },
                {
                    "label": "Pending imports",
                    "value": ImportJob.objects.filter(status=ImportJob.Status.PENDING).count(),
                    "tone": "warning",
                },
            ]
        )

    return {
        "title": ROLE_COPY[role]["title"],
        "intro": ROLE_COPY[role]["intro"],
        "focus_items": ROLE_COPY[role]["focus_items"],
        "metrics": metrics,
        "refresh_url": reverse("analytics:dashboard-metrics"),
        "system_counts": {
            "stores": Store.objects.count(),
            "regions": Region.objects.count(),
            "hubs": SupplyHub.objects.count(),
            "events": SyncOutboxEvent.objects.count(),
        },
    }
