from copy import deepcopy
from dataclasses import dataclass

from django.urls import reverse

from .models import User


@dataclass(frozen=True)
class NavigationItem:
    label: str
    route_name: str


ROLE_METADATA = {
    User.Role.ACCOUNT_USER: {
        "label": "Customer",
        "template": "customer/dashboard.html",
        "dashboard_route": "customer-dashboard",
        "description": "Track orders, preferences, and your preferred pickup store.",
        "navigation": [
            NavigationItem("Stores", "stores:index"),
            NavigationItem("Recommendations", "orders:recommendations"),
            NavigationItem("Favorites", "orders:favorites"),
            NavigationItem("Preferences", "account-preferences"),
            NavigationItem("Orders", "orders:history"),
            NavigationItem("Cart", "orders:cart"),
        ],
    },
    User.Role.MANAGER: {
        "label": "Manager",
        "template": "manager/dashboard.html",
        "dashboard_route": "manager-dashboard",
        "description": "Run a single store with inventory, orders, and revenue visibility.",
        "navigation": [
            NavigationItem("Order Queue", "orders:index"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Payments", "payments:index"),
            NavigationItem("Maintenance", "maintenance:index"),
        ],
    },
    User.Role.ADMIN: {
        "label": "Admin",
        "template": "admin/dashboard.html",
        "dashboard_route": "admin-dashboard",
        "description": "Manage accounts, roles, and store governance without owning operations.",
        "navigation": [
            NavigationItem("Team", "admin-users"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Analytics", "analytics:index"),
        ],
    },
    User.Role.LOGISTICS_MANAGER: {
        "label": "Logistics Manager",
        "template": "logistics/dashboard.html",
        "dashboard_route": "logistics-dashboard",
        "description": "Coordinate supply hubs, regional transfers, imports, and sync health.",
        "navigation": [
            NavigationItem("Supply Hubs", "supply_hubs:index"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Imports", "imports:index"),
            NavigationItem("Sync", "sync:index"),
            NavigationItem("Analytics", "analytics:index"),
        ],
    },
    User.Role.REPAIR_STAFF: {
        "label": "Repair Staff",
        "template": "repair/dashboard.html",
        "dashboard_route": "repair-dashboard",
        "description": "Prioritize machine health, repair queues, and regional service coverage.",
        "navigation": [
            NavigationItem("Maintenance", "maintenance:index"),
            NavigationItem("Stores", "stores:index"),
            NavigationItem("Imports", "imports:index"),
        ],
    },
    User.Role.SUPER_ADMIN: {
        "label": "Super Admin",
        "template": "super_admin/dashboard.html",
        "dashboard_route": "super-admin-dashboard",
        "description": "See cross-region operations while preserving store and region ownership.",
        "navigation": [
            NavigationItem("Stores", "stores:index"),
            NavigationItem("Orders", "orders:index"),
            NavigationItem("Payments", "payments:index"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Supply Hubs", "supply_hubs:index"),
            NavigationItem("Maintenance", "maintenance:index"),
            NavigationItem("Imports", "imports:index"),
            NavigationItem("Sync", "sync:index"),
            NavigationItem("Analytics", "analytics:index"),
        ],
    },
}


def get_role_metadata(role: str) -> dict:
    return deepcopy(ROLE_METADATA[role])


def get_role_cards() -> list[dict]:
    return [
        {
            "title": metadata["label"],
            "description": metadata["description"],
            "dashboard_route": metadata["dashboard_route"],
        }
        for metadata in ROLE_METADATA.values()
    ]


def get_dashboard_template(role: str) -> str:
    return ROLE_METADATA[role]["template"]


def get_dashboard_route_name(role: str) -> str:
    return ROLE_METADATA[role]["dashboard_route"]


def build_navigation(user) -> list[dict]:
    items = [{"label": "Home", "url": reverse("home")}]
    if not getattr(user, "is_authenticated", False):
        items.append({"label": "Stores", "url": reverse("stores:index")})
        items.append({"label": "Guest Lookup", "url": reverse("orders:guest-lookup")})
        items.append({"label": "Sign in", "url": reverse("login")})
        items.append({"label": "Register", "url": reverse("register")})
        return items

    metadata = get_role_metadata(user.role)
    unread_notifications = user.notifications.filter(is_read=False).count()
    items.append({"label": "Dashboard", "url": reverse(metadata["dashboard_route"])})
    for nav_item in metadata["navigation"]:
        items.append({"label": nav_item.label, "url": reverse(nav_item.route_name)})
    items.append(
        {
            "label": "Notifications",
            "url": reverse("notifications:index"),
            "badge": unread_notifications,
            "badge_id": "nav-notification-badge",
        }
    )
    items.append({"label": "Log out", "url": reverse("logout"), "method": "post"})
    return items
