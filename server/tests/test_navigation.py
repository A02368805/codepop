from apps.users.selectors import build_brandmark, build_navigation
from apps.users.services import get_post_login_url
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse

from .helpers import assign_region, assign_store, make_region, make_store, make_user


class NavigationSelectorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")

        cls.account_user = make_user(
            email="account-nav@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="manager-nav@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.admin = make_user(
            email="admin-nav@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.logistics = make_user(
            email="logistics-nav@test.local",
            role="logistics_manager",
            default_region=cls.region,
        )
        cls.repair = make_user(
            email="repair-nav@test.local",
            role="repair_staff",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.super_admin = make_user(
            email="super-nav@test.local",
            role="super_admin",
            default_region=cls.region,
            is_superuser=True,
        )

        assign_store(cls.manager, cls.store)
        assign_store(cls.admin, cls.store)
        assign_store(cls.repair, cls.store)
        assign_region(cls.logistics, cls.region)

    def _labels(self, items):
        return [item["label"] for item in items]

    def _item_for_label(self, items, label):
        return next(item for item in items if item["label"] == label)

    def test_anonymous_nav_and_logo_targets(self):
        nav = build_navigation(AnonymousUser())
        brand = build_brandmark(AnonymousUser())

        self.assertEqual(
            self._labels(nav), ["Browse Drinks", "Help", "Sign In", "Create Account"]
        )
        self.assertEqual(
            self._item_for_label(nav, "Browse Drinks")["url"], reverse("stores:index")
        )
        self.assertEqual(
            self._item_for_label(nav, "Help")["url"], reverse("support:index")
        )
        self.assertEqual(self._item_for_label(nav, "Sign In")["url"], reverse("login"))
        self.assertEqual(
            self._item_for_label(nav, "Create Account")["url"], reverse("register")
        )
        self.assertTrue(brand["is_clickable"])
        self.assertEqual(brand["url"], reverse("home"))

    def test_account_user_nav_matches_customer_menu(self):
        nav = build_navigation(self.account_user)
        brand = build_brandmark(self.account_user)

        self.assertEqual(
            self._labels(nav),
            [
                "Browse Drinks",
                "My Orders",
                "Cart",
                "Favorites",
                "Help",
                "Updates",
                "Log out",
            ],
        )
        self.assertEqual(
            self._item_for_label(nav, "Browse Drinks")["url"], reverse("stores:index")
        )
        self.assertEqual(
            self._item_for_label(nav, "My Orders")["url"], reverse("orders:history")
        )
        self.assertEqual(
            self._item_for_label(nav, "Cart")["url"], reverse("orders:cart")
        )
        self.assertEqual(
            self._item_for_label(nav, "Help")["url"], reverse("support:index")
        )
        self.assertEqual(
            self._item_for_label(nav, "Updates")["url"],
            reverse("notifications:index"),
        )
        self.assertEqual(
            self._item_for_label(nav, "Updates")["icon"],
            "notification",
        )
        self.assertTrue(brand["is_clickable"])
        self.assertEqual(brand["url"], reverse("orders:recommendations"))
        self.assertEqual(
            get_post_login_url(self.account_user), reverse("orders:recommendations")
        )

    def test_manager_nav_matches_operational_menu(self):
        nav = build_navigation(self.manager)

        self.assertEqual(
            self._labels(nav),
            [
                "Dashboard",
                "Inventory",
                "Maintenance",
                "Order Queue",
                "Analytics",
                "Updates",
                "Log out",
            ],
        )
        self.assertEqual(
            self._item_for_label(nav, "Dashboard")["url"],
            reverse("manager-dashboard"),
        )

    def test_logistics_nav_matches_operational_menu(self):
        nav = build_navigation(self.logistics)

        self.assertEqual(
            self._labels(nav),
            [
                "Dashboard",
                "Supply Hub",
                "Inventory",
                "Imports",
                "Sync",
                "Analytics",
                "Updates",
                "Log out",
            ],
        )
        self.assertEqual(
            self._item_for_label(nav, "Dashboard")["url"],
            reverse("logistics-dashboard"),
        )

    def test_repair_nav_matches_operational_menu(self):
        nav = build_navigation(self.repair)

        self.assertEqual(
            self._labels(nav),
            ["Dashboard", "Maintenance", "Imports", "Updates", "Log out"],
        )
        self.assertEqual(
            self._item_for_label(nav, "Dashboard")["url"],
            reverse("repair-dashboard"),
        )

    def test_admin_nav_places_sync_after_notifications_with_icon(self):
        nav = build_navigation(self.admin)

        self.assertEqual(
            self._labels(nav),
            [
                "Dashboard",
                "Inventory",
                "Team",
                "Analytics",
                "Updates",
                "Sync",
                "Log out",
            ],
        )
        sync_item = self._item_for_label(nav, "Sync")
        self.assertEqual(sync_item["url"], reverse("sync:index"))
        self.assertEqual(sync_item["icon"], "sync")

    def test_super_admin_nav_uses_requested_order_and_sync_icon(self):
        nav = build_navigation(self.super_admin)

        self.assertEqual(
            self._labels(nav),
            [
                "Dashboard",
                "Analytics",
                "Inventory",
                "Maintenance",
                "Order Queue",
                "Supply Hubs",
                "Imports",
                "Updates",
                "Sync",
                "Log out",
            ],
        )
        sync_item = self._item_for_label(nav, "Sync")
        self.assertEqual(sync_item["url"], reverse("sync:index"))
        self.assertEqual(sync_item["icon"], "sync")

    def test_staff_brandmark_routes_to_role_dashboard(self):
        expected_routes = [
            (self.manager, "manager-dashboard"),
            (self.admin, "admin-dashboard"),
            (self.logistics, "logistics-dashboard"),
            (self.repair, "repair-dashboard"),
            (self.super_admin, "super-admin-dashboard"),
        ]
        for user, route_name in expected_routes:
            with self.subTest(role=user.role):
                brand = build_brandmark(user)
                self.assertTrue(brand["is_clickable"])
                self.assertEqual(brand["url"], reverse(route_name))
                self.assertEqual(get_post_login_url(user), reverse(route_name))
