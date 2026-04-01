from copy import deepcopy
from dataclasses import dataclass

from django.urls import reverse

from .models import User


@dataclass(frozen=True)
class NavigationItem:
    label: str
    route_name: str
    icon: str | None = None


ROLE_METADATA = {
    User.Role.ACCOUNT_USER: {
        "label": "Customer",
        "template": "customer/dashboard.html",
        "dashboard_route": "customer-dashboard",
        "description": "Track orders, preferences, and your preferred pickup store.",
        "navigation": [
            NavigationItem("Stores", "stores:index"),
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
            NavigationItem("Dashboard", "manager-dashboard"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Maintenance", "maintenance:index"),
            NavigationItem("Order Queue", "orders:index"),
            NavigationItem("Analytics", "analytics:index"),
        ],
    },
    User.Role.ADMIN: {
        "label": "Admin",
        "template": "admin/dashboard.html",
        "dashboard_route": "admin-dashboard",
        "description": "Manage accounts, roles, and store governance without owning operations.",
        "navigation": [
            NavigationItem("Dashboard", "admin-dashboard"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Team", "admin-users"),
            NavigationItem("Analytics", "analytics:index"),
        ],
        "post_notification_navigation": [
            NavigationItem("Sync", "sync:index", icon="sync"),
        ],
    },
    User.Role.LOGISTICS_MANAGER: {
        "label": "Logistics Manager",
        "template": "logistics/dashboard.html",
        "dashboard_route": "logistics-dashboard",
        "description": "Coordinate supply hubs, regional transfers, imports, and sync health.",
        "navigation": [
            NavigationItem("Dashboard", "logistics-dashboard"),
            NavigationItem("Supply Hub", "supply_hubs:index"),
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
            NavigationItem("Dashboard", "repair-dashboard"),
            NavigationItem("Maintenance", "maintenance:index"),
            NavigationItem("Imports", "imports:index"),
        ],
    },
    User.Role.SUPER_ADMIN: {
        "label": "Super Admin",
        "template": "super_admin/dashboard.html",
        "dashboard_route": "super-admin-dashboard",
        "description": "See cross-region operations while preserving store and region ownership.",
        "navigation": [
            NavigationItem("Dashboard", "super-admin-dashboard"),
            NavigationItem("Analytics", "analytics:index"),
            NavigationItem("Inventory", "inventory:index"),
            NavigationItem("Maintenance", "maintenance:index"),
            NavigationItem("Order Queue", "orders:index"),
            NavigationItem("Supply Hubs", "supply_hubs:index"),
            NavigationItem("Imports", "imports:index"),
        ],
        "post_notification_navigation": [
            NavigationItem("Sync", "sync:index", icon="sync"),
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


def build_brandmark(user) -> dict:
    if not getattr(user, "is_authenticated", False):
        return {"url": reverse("home"), "is_clickable": True}
    if user.role == User.Role.ACCOUNT_USER:
        return {"url": reverse("orders:recommendations"), "is_clickable": True}
    return {"url": "", "is_clickable": False}


def build_navigation(user) -> list[dict]:
    if not getattr(user, "is_authenticated", False):
        items = []
        items.append({"label": "Stores", "url": reverse("stores:index")})
        items.append({"label": "Sign In", "url": reverse("login")})
        items.append({"label": "Sign up", "url": reverse("register")})
        return items

    metadata = get_role_metadata(user.role)
    items = []
    unread_notifications = user.notifications.filter(is_read=False).count()
    for nav_item in metadata["navigation"]:
        item = {"label": nav_item.label, "url": reverse(nav_item.route_name)}
        if nav_item.icon:
            item["icon"] = nav_item.icon
        items.append(item)
    items.append(
        {
            "label": "Notifications",
            "url": reverse("notifications:index"),
            "badge": unread_notifications,
            "badge_id": "nav-notification-badge",
            "icon": "notification",
        }
    )
    for nav_item in metadata.get("post_notification_navigation", []):
        item = {"label": nav_item.label, "url": reverse(nav_item.route_name)}
        if nav_item.icon:
            item["icon"] = nav_item.icon
        items.append(item)
    items.append({"label": "Log out", "url": reverse("logout"), "method": "post"})
    return items
