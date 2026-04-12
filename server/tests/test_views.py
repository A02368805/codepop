from datetime import timedelta
from decimal import Decimal

from apps.imports.models import ImportJob
from apps.inventory.models import InventoryItem, LocalSupplier, SupplierReplenishment
from apps.inventory.services import get_store_balance, request_transfer
from apps.notifications.models import Notification
from apps.orders.cart import SESSION_CART_KEY
from apps.orders.models import Order
from apps.orders.pickup import pickup_time_choices
from apps.orders.services import create_order, transition_order_status
from apps.payments.models import PaymentTransaction
from apps.payments.services import record_payment_pending, record_payment_success
from apps.supply_hubs.models import SupplyTransfer
from apps.sync.models import AuditLog
from apps.users.models import FavoriteDrink, TastePreference
from apps.users.services import save_preference_profile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


def seed_menu_inventory(store):
    inventory_rows = [
        ("BASE-LEMON-LIME", "Lemon Lime Base", "soda", "5.00"),
        ("SYRUP-STRAWBERRY", "Strawberry Syrup", "syrup", "5.00"),
        ("CUPS-24OZ", "24oz Cups", "cups", "50.00"),
        ("LIDS-24OZ", "24oz Lids", "lids", "50.00"),
    ]
    for sku, name, category, threshold in inventory_rows:
        item = make_inventory_item(
            sku=sku, name=name, category=category, threshold=threshold
        )
        balance = get_store_balance(store, item)
        balance.on_hand_quantity = Decimal("250.00")
        balance.reorder_threshold = Decimal(threshold)
        balance.save()


class CustomerOrderingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.region_alt = make_region(code="G", name="Boise, ID")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.store_alt = make_store(
            store_code="G001",
            region=cls.region_alt,
            name="Boise Central",
        )
        cls.customer = make_user(
            email="customer-flow@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        seed_menu_inventory(cls.store)

    def _add_drink_to_cart(self, client):
        return client.post(
            reverse("orders:customize", args=[self.store.store_code, "berry-burst"]),
            {
                "size": "medium",
                "soda": "lemon-lime",
                "syrups": ["strawberry"],
                "add_ins": [],
                "quantity": 2,
                "notes": "light ice",
            },
            follow=True,
        )

    def _future_pickup_value(self):
        return pickup_time_choices(now=timezone.now())[1][0]

    @override_settings(STORE_ID="store-c")
    def test_topbar_shows_current_store_and_region_in_distributed_mode(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("orders:menu", args=[self.store.store_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Node")
        self.assertContains(response, f"{self.store.name} ({self.store.store_code})")
        self.assertContains(response, f"Region {self.region.code}: {self.region.name}")

    @override_settings(STORE_ID="")
    def test_topbar_hides_distributed_indicator_when_node_unconfigured(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("orders:menu", args=[self.store.store_code]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Current Node")

    def test_account_user_can_complete_checkout_and_save_favorite(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("orders:customize", args=[self.store.store_code, "berry-burst"]),
            {
                "size": "medium",
                "soda": "lemon-lime",
                "syrups": ["strawberry"],
                "add_ins": [],
                "quantity": 2,
                "notes": "extra fizz",
                "save_favorite": "1",
            },
            follow=True,
        )

        self.assertContains(response, "Added Berry Burst to your cart.")
        response = self.client.post(
            reverse("orders:checkout"),
            {"pickup_time_choice": self._future_pickup_value()},
            follow=True,
        )

        order = Order.objects.get()
        self.assertEqual(order.order_type, Order.OrderType.ACCOUNT)
        self.assertEqual(order.store, self.store)
        self.assertEqual(order.status, Order.Status.QUEUED)
        self.assertEqual(
            order.payment_transaction.provider, PaymentTransaction.Provider.MOCK
        )
        self.assertEqual(
            order.payment_transaction.status, PaymentTransaction.Status.SUCCEEDED
        )
        self.assertTrue(
            FavoriteDrink.objects.filter(
                user=self.customer, recipe_key="berry-burst"
            ).exists()
        )
        self.assertEqual(order.items.first().display_name_snapshot, "Berry Burst")
        self.assertContains(response, order.public_order_code)

    def test_guest_lookup_flow_works_without_creating_a_user(self):
        guest_client = Client()
        self._add_drink_to_cart(guest_client)
        response = guest_client.post(
            reverse("orders:checkout"),
            {
                "pickup_time_choice": self._future_pickup_value(),
                "guest_name": "Taylor Guest",
                "guest_email": "guest-flow@test.local",
                "guest_phone_number": "8015550101",
            },
            follow=True,
        )

        order = Order.objects.get(order_type=Order.OrderType.GUEST)
        self.assertContains(response, order.guest_contact.lookup_code)

        lookup_client = Client()
        response = lookup_client.post(
            reverse("orders:guest-lookup"),
            {"lookup_code": order.guest_contact.lookup_code},
            follow=True,
        )
        self.assertContains(response, order.public_order_code)
        self.assertEqual(
            Order.objects.filter(order_type=Order.OrderType.GUEST).count(), 1
        )

    def test_customer_status_page_hides_cancel_after_preparing(self):
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("0.35"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.35",
                        "inventory_requirements": [
                            {"sku": "BASE-LEMON-LIME", "quantity": "0.50"},
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "0.50"},
                            {"sku": "CUPS-24OZ", "quantity": "1.00"},
                            {"sku": "LIDS-24OZ", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )
        record_payment_pending(order, payment_intent_id="pi_customer_status")
        record_payment_success(
            order, payment_intent_id="pi_customer_status", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        self.client.force_login(self.customer)
        response = self.client.get(
            reverse("orders:detail", args=[order.public_order_code])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cancel order")
        self.assertContains(response, "This order can no longer be canceled online.")

    def test_checkout_with_stale_inventory_snapshot_fails_gracefully(self):
        self.client.force_login(self.customer)
        self._add_drink_to_cart(self.client)

        session = self.client.session
        cart = session[SESSION_CART_KEY]
        cart["items"][0]["customizations"]["inventory_requirements"] = [
            {"sku": "BASE-COLA", "quantity": "1.00"}
        ]
        session[SESSION_CART_KEY] = cart
        session.save()

        response = self.client.post(
            reverse("orders:checkout"),
            {"pickup_time_choice": self._future_pickup_value()},
            follow=True,
        )

        order = Order.objects.latest("created_at")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "outdated recipe snapshot")
        self.assertEqual(order.status, Order.Status.CANCELED)

    def test_checkout_with_mixed_store_cart_snapshot_is_blocked(self):
        self.client.force_login(self.customer)
        self._add_drink_to_cart(self.client)

        session = self.client.session
        cart = session[SESSION_CART_KEY]
        cart["items"][0]["store_code_snapshot"] = "G001"
        session[SESSION_CART_KEY] = cart
        session.save()

        response = self.client.post(
            reverse("orders:checkout"),
            {"pickup_time_choice": self._future_pickup_value()},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "includes items from a different store")
        self.assertEqual(Order.objects.count(), 0)
        cart_after = self.client.session[SESSION_CART_KEY]
        self.assertEqual(cart_after["items"], [])

    def test_staff_roles_cannot_enter_customer_ordering_flow(self):
        manager = make_user(
            email="customer-block@test.local",
            role="manager",
            preferred_store=self.store,
            default_region=self.region,
        )
        assign_store(manager, self.store)

        self.client.force_login(manager)
        response = self.client.get(reverse("orders:menu", args=[self.store.store_code]))
        self.assertEqual(response.status_code, 403)
        self.assertIn("outside your current scope", response.content.decode())

    def test_account_preferences_save_multiple_structured_choices(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("account-preferences"),
            {
                "preferred_store": self.store_alt.id,
                "favorite_sodas": ["sprite", "root-beer"],
                "favorite_syrups": ["strawberry", "coconut"],
                "favorite_add_ins": ["cream", "coconut-cream"],
                "favorite_ice_creams": ["scoop-vanilla"],
                "disliked_ingredients": ["grapefruit"],
                "dietary_preferences": ["caffeine-free"],
                "sweetness_preference": "sweet",
                "adventurousness_preference": "balanced",
            },
            follow=False,
        )

        self.customer.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("account-preferences"))
        follow_response = self.client.get(response.headers["Location"], follow=True)
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(
            follow_response,
            "Preferences saved. Your taste profile is now applied across FloatStack.",
        )
        self.assertEqual(self.customer.preferred_store_id, self.store_alt.id)
        self.assertEqual(self.customer.default_region_id, self.region_alt.id)
        self.assertEqual(self.customer.sweetness_preference, "sweet")
        self.assertEqual(
            self.customer.adventurousness_preference,
            "balanced",
        )
        self.assertTrue(
            TastePreference.objects.filter(
                user=self.customer,
                preference_type=TastePreference.PreferenceType.FAVORITE_SODA,
                ingredient_name="sprite",
            ).exists()
        )
        self.assertTrue(
            TastePreference.objects.filter(
                user=self.customer,
                preference_type=TastePreference.PreferenceType.FAVORITE_ADD_IN,
                ingredient_name="coconut-cream",
            ).exists()
        )
        self.assertTrue(
            TastePreference.objects.filter(
                user=self.customer,
                preference_type=TastePreference.PreferenceType.FAVORITE_ICE_CREAM,
                ingredient_name="scoop-vanilla",
            ).exists()
        )

    def test_ai_fill_uses_saved_preferences_and_returns_builder_selection(self):
        save_preference_profile(
            user=self.customer,
            favorite_sodas=["sprite"],
            favorite_syrups=["strawberry", "coconut"],
            favorite_add_ins=["cream"],
            favorite_ice_creams=["scoop-vanilla"],
            disliked_ingredients=[],
            dietary_preferences=[],
            sweetness_preference="sweet",
            adventurousness_preference="balanced",
        )
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("orders:ai-fill", args=[self.store.store_code, "berry-burst"]),
            {
                "size": "medium",
                "soda": "",
                "syrups": [],
                "add_ins": [],
                "ice_cream": "",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["selection"]["soda"], "sprite")
        self.assertTrue(
            set(payload["selection"]["syrups"]).intersection({"strawberry", "coconut"})
        )
        self.assertIn("assistant_html", payload)

    def test_customer_dashboard_shows_builder_entry_points_and_direct_recommendation_links(
        self,
    ):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("customer-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open AI builder")
        self.assertContains(response, "Open manual builder")
        self.assertContains(
            response,
            reverse("orders:menu", args=[self.store.store_code]),
        )
        self.assertContains(
            response,
            f"{reverse('orders:menu', args=[self.store.store_code])}?open_ai=1",
        )
        self.assertContains(
            response,
            reverse("orders:menu", args=[self.store.store_code]),
        )

    def test_recommendations_page_shows_builder_actions_and_change_store(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("orders:recommendations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recommended Drinks")
        self.assertContains(response, "Update taste profile")
        self.assertContains(response, "Create this drink")
        self.assertContains(
            response,
            reverse("orders:customize", args=[self.store.store_code, "berry-burst"]),
        )

    def test_account_preferences_save_defaults_missing_style_fields(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("account-preferences"),
            {
                "preferred_store": self.store.id,
                "favorite_sodas": ["sprite"],
                "favorite_syrups": [],
                "favorite_add_ins": [],
                "favorite_ice_creams": [],
                "disliked_ingredients": [],
                "dietary_preferences": [],
            },
            follow=False,
        )

        self.customer.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("account-preferences"))
        self.assertEqual(
            self.customer.sweetness_preference,
            self.customer.SweetnessPreference.BALANCED,
        )
        self.assertEqual(
            self.customer.adventurousness_preference,
            self.customer.AdventurousnessPreference.BALANCED,
        )


class DashboardAndHtmxViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region_c = make_region(code="C", name="Logan, UT")
        cls.region_g = make_region(
            code="G",
            name="Boise, ID",
            hub_city="Boise",
            hub_state_code="ID",
            latitude="43.615021",
            longitude="-116.202316",
        )
        cls.store_c1 = make_store(
            store_code="C001", region=cls.region_c, name="Logan Main"
        )
        cls.store_c2 = make_store(
            store_code="C002",
            region=cls.region_c,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.store_g1 = make_store(
            store_code="G001",
            region=cls.region_g,
            name="Boise Capitol",
            city="Boise",
            state_code="ID",
            address_line_1="50 Idaho St",
            postal_code="83702",
            latitude="43.615018",
            longitude="-116.202313",
        )

        cls.manager = make_user(
            email="manager-views@test.local",
            role="manager",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.admin = make_user(
            email="admin-views@test.local",
            role="admin",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.logistics = make_user(
            email="logistics-views@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.repair = make_user(
            email="repair-views@test.local",
            role="repair_staff",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.super_admin = make_user(
            email="super-views@test.local",
            role="super_admin",
            default_region=cls.region_c,
            is_superuser=True,
        )

        assign_store(cls.manager, cls.store_c1)
        assign_store(cls.admin, cls.store_c1)
        assign_store(cls.repair, cls.store_c1)
        assign_region(cls.logistics, cls.region_c)

        cls.inventory_item = make_inventory_item(
            sku="SYRUP-STRAWBERRY", name="Strawberry Syrup"
        )
        cls.cup_item = make_inventory_item(
            sku="CUPS-24OZ",
            name="24oz Cups",
            category="cups",
            threshold="100.00",
        )
        balance = get_store_balance(cls.store_c1, cls.inventory_item)
        balance.on_hand_quantity = Decimal("10.00")
        balance.reorder_threshold = Decimal("5.00")
        balance.save()
        cup_balance = get_store_balance(cls.store_c1, cls.cup_item)
        cup_balance.on_hand_quantity = Decimal("40.00")
        cup_balance.reorder_threshold = Decimal("100.00")
        cup_balance.save()
        cls.local_supplier = LocalSupplier.objects.create(
            name="Cache Valley Vendor",
            service_region=cls.region_c,
            contact_name="Morgan Supply",
            email="vendor@test.local",
            phone_number="8015550133",
            item_categories_json=["syrup", "cups"],
            is_active=True,
        )

        cls.queue_order = create_order(
            store=cls.store_c1,
            customer=None,
            guest_contact={"display_name": "Walk Up", "email": "walkup@test.local"},
            items=[
                {
                    "display_name": "Queue Test",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=cls.manager,
        )
        record_payment_pending(cls.queue_order, payment_intent_id="pi_queue_test")
        record_payment_success(
            cls.queue_order, payment_intent_id="pi_queue_test", actor=cls.manager
        )
        transition_order_status(cls.queue_order, Order.Status.QUEUED, actor=cls.manager)

        cls.out_of_scope_order = create_order(
            store=cls.store_c2,
            customer=None,
            guest_contact={"display_name": "Other Store", "email": "other@test.local"},
            items=[
                {
                    "display_name": "Scope Test",
                    "size": "medium",
                    "base_price": Decimal("4.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=cls.super_admin,
        )

        cls.transfer = request_transfer(
            requested_by=cls.manager,
            source_store=cls.store_c1,
            destination_store=cls.store_c2,
            line_items=[
                {
                    "inventory_item": cls.inventory_item,
                    "quantity_requested": Decimal("2.00"),
                }
            ],
            notes="Need more syrup",
            is_ai_draft=True,
        )

    def test_role_dashboards_render_expected_sections(self):
        dashboard_expectations = [
            (self.manager, "manager-dashboard", "Orders awaiting store action"),
            (self.admin, "admin-dashboard", "Managed Users"),
            (self.logistics, "logistics-dashboard", "Pending Transfers"),
            (self.repair, "repair-dashboard", "Assigned Work"),
            (self.super_admin, "super-admin-dashboard", "Region Comparison"),
        ]
        for user, route_name, expected_text in dashboard_expectations:
            with self.subTest(route=route_name):
                self.client.force_login(user)
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)

    def test_wrong_dashboard_returns_friendly_403(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("outside your current scope", response.content.decode())

    def test_inventory_adjust_htmx_updates_the_row(self):
        self.client.force_login(self.manager)
        balance = get_store_balance(self.store_c1, self.inventory_item)
        response = self.client.post(
            reverse("inventory:adjust", args=[balance.id]),
            {"delta": "1.00", "reason": "count correction"},
            HTTP_HX_REQUEST="true",
        )
        balance.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(balance.on_hand_quantity, Decimal("11.00"))
        self.assertContains(response, "11.00")

    def test_inventory_adjust_step_size_matches_item_unit_expectation(self):
        self.client.force_login(self.manager)
        liquid_item = InventoryItem.objects.create(
            sku="SYRUP-VOLUME-TEST",
            name="Volume Syrup Test",
            category=InventoryItem.Category.SYRUP,
            unit_of_measure="oz",
            default_low_stock_threshold=Decimal("5.00"),
        )
        syrup_balance = get_store_balance(self.store_c1, liquid_item)
        syrup_balance.on_hand_quantity = Decimal("10.00")
        syrup_balance.reorder_threshold = Decimal("5.00")
        syrup_balance.save()
        cup_balance = get_store_balance(self.store_c1, self.cup_item)

        syrup_response = self.client.post(
            reverse("inventory:adjust", args=[syrup_balance.id]),
            {"delta": "0.50", "reason": "syrup calibration"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(syrup_response.status_code, 200)
        self.assertContains(
            syrup_response,
            'name="delta" step="0.01" value="1"',
            html=False,
        )

        cup_response = self.client.post(
            reverse("inventory:adjust", args=[cup_balance.id]),
            {"delta": "1", "reason": "cup count correction"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(cup_response.status_code, 200)
        self.assertContains(
            cup_response,
            'name="delta" step="1" value="1"',
            html=False,
        )

    def test_inventory_filter_narrows_to_selected_store(self):
        second_balance = get_store_balance(self.store_c2, self.inventory_item)
        second_balance.on_hand_quantity = Decimal("3.00")
        second_balance.reorder_threshold = Decimal("5.00")
        second_balance.save()

        self.client.force_login(self.super_admin)
        response = self.client.get(
            reverse("inventory:index"),
            {"store": str(self.store_c1.id)},
        )

        grouped_balances = response.context["grouped_balances"]
        self.assertGreaterEqual(len(grouped_balances), 1)
        for group in grouped_balances:
            self.assertEqual(len(group["stores"]), 1)
            self.assertEqual(group["stores"][0]["balance"].store, self.store_c1)

    def test_manager_queue_actions_render_confirm_prompts_and_valid_next_step_only(
        self,
    ):
        self.client.force_login(self.manager)

        queued_response = self.client.get(reverse("orders:index"))
        preparing_url = reverse("orders:mark-preparing", args=[self.queue_order.id])
        ready_url = reverse("orders:mark-ready", args=[self.queue_order.id])
        picked_up_url = reverse("orders:mark-picked-up", args=[self.queue_order.id])

        self.assertEqual(queued_response.status_code, 200)
        self.assertContains(queued_response, preparing_url)
        self.assertContains(
            queued_response,
            'hx-confirm="Mark order as preparing?"',
            html=False,
        )
        self.assertContains(
            queued_response,
            "hx-disabled-elt=\"find button[type='submit']\"",
            html=False,
        )
        self.assertContains(queued_response, "Updating...")
        self.assertNotContains(queued_response, ready_url)
        self.assertNotContains(queued_response, picked_up_url)

        transition_order_status(
            self.queue_order,
            Order.Status.PREPARING,
            actor=self.manager,
        )
        preparing_response = self.client.get(reverse("orders:index"))
        self.assertContains(preparing_response, ready_url)
        self.assertContains(
            preparing_response,
            "Mark order as ready? This cannot be undone from the queue.",
        )
        self.assertNotContains(preparing_response, preparing_url)
        self.assertNotContains(preparing_response, picked_up_url)

        transition_order_status(
            self.queue_order,
            Order.Status.READY,
            actor=self.manager,
        )
        ready_response = self.client.get(reverse("orders:index"))
        self.assertContains(ready_response, picked_up_url)
        self.assertContains(
            ready_response,
            "Mark order as picked up? This completes the order.",
        )
        self.assertNotContains(ready_response, preparing_url)
        self.assertNotContains(ready_response, ready_url)

    def test_order_transition_htmx_moves_queue_forward(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("orders:mark-preparing", args=[self.queue_order.id]),
            HTTP_HX_REQUEST="true",
        )
        self.queue_order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.queue_order.status, Order.Status.PREPARING)
        self.assertContains(response, "Preparing")
        self.assertContains(response, '<table class="data-table">', html=False)
        self.assertContains(
            response,
            reverse("orders:mark-ready", args=[self.queue_order.id]),
        )

    def test_admin_cannot_transition_order_status(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("orders:mark-preparing", args=[self.queue_order.id]),
            HTTP_HX_REQUEST="true",
        )

        self.queue_order.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.queue_order.status, Order.Status.QUEUED)

    def test_manager_queue_rows_are_clickable_beyond_order_code(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("orders:index"))
        detail_url = reverse("orders:detail", args=[self.queue_order.public_order_code])
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'class="queue-row-link" href="{detail_url}"',
            count=4,
            html=False,
        )
        self.assertContains(
            response,
            f'class="queue-row-link queue-row-link--code" href="{detail_url}"',
            count=1,
            html=False,
        )

    def test_transfer_approval_htmx_updates_transfer_panel(self):
        self.client.force_login(self.logistics)
        response = self.client.post(
            reverse("supply_hubs:approve-transfer", args=[self.transfer.id]),
            HTTP_HX_REQUEST="true",
        )
        self.transfer.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.transfer.status, self.transfer.Status.APPROVED)
        self.assertContains(response, "Approved")

    def test_manager_cannot_approve_transfer_via_htmx_action(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("supply_hubs:approve-transfer", args=[self.transfer.id]),
            HTTP_HX_REQUEST="true",
        )

        self.transfer.refresh_from_db()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.transfer.status, self.transfer.Status.REQUESTED)
        self.assertContains(response, "cannot approve", status_code=409)

    def test_logistics_can_create_transfer_request_from_workspace(self):
        self.client.force_login(self.logistics)
        response = self.client.post(
            reverse("supply_hubs:create-transfer"),
            {
                "destination_store": str(self.store_c2.id),
                "inventory_item": str(self.inventory_item.id),
                "quantity_requested": "2.00",
                "source_kind": "auto",
                "notes": "restock for weekend",
            },
            follow=True,
        )

        created_transfer = SupplyTransfer.objects.exclude(pk=self.transfer.id).latest(
            "requested_at"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(created_transfer.requested_by, self.logistics)
        self.assertEqual(created_transfer.destination_store, self.store_c2)
        self.assertEqual(created_transfer.source_store, self.store_c1)
        self.assertContains(response, "Transfer requested")

    def test_logistics_can_place_and_receive_supplier_order(self):
        self.client.force_login(self.logistics)
        response = self.client.post(
            reverse("supply_hubs:create-supplier-order"),
            {
                "store": str(self.store_c1.id),
                "supplier": str(self.local_supplier.id),
                "inventory_item": str(self.cup_item.id),
                "quantity_requested": "80.00",
                "expected_delivery_date": timezone.now().date().isoformat(),
                "unit_cost": "17.50",
                "notes": "cups for event traffic",
            },
            follow=True,
        )

        replenishment = SupplierReplenishment.objects.latest("ordered_at")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(replenishment.status, SupplierReplenishment.Status.ORDERED)
        self.assertEqual(replenishment.quantity_requested, Decimal("250"))
        self.assertContains(response, "Supplier order placed")

        balance = get_store_balance(self.store_c1, self.cup_item)
        response = self.client.post(
            reverse("supply_hubs:receive-supplier-order", args=[replenishment.id]),
            HTTP_HX_REQUEST="true",
        )
        replenishment.refresh_from_db()
        balance.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(replenishment.status, SupplierReplenishment.Status.RECEIVED)
        self.assertEqual(balance.on_hand_quantity, Decimal("290.00"))
        self.assertContains(response, "Received")

    def test_manager_cannot_view_other_store_order(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("orders:detail", args=[self.out_of_scope_order.public_order_code])
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("outside your current scope", response.content.decode())

    def test_custom_admin_users_route_resolves_successfully(self):
        self.client.force_login(self.admin)
        response = self.client.get("/admin/users/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scoped User Management")

    def test_supply_usage_import_htmx_renders_history_panel(self):
        self.client.force_login(self.logistics)
        upload = SimpleUploadedFile(
            "usage.csv",
            b"store_code,inventory_sku,usage_date,quantity_used\nC001,SYRUP-STRAWBERRY,2026-03-18,2.50\n",
            content_type="text/csv",
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("imports:supply-usage"),
                {"file": upload},
                HTTP_HX_REQUEST="true",
            )
        self.assertEqual(response.status_code, 200)
        job = (
            ImportJob.objects.filter(original_filename="usage.csv")
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(job)
        self.assertIn(
            job.status,
            {
                ImportJob.Status.PENDING,
                ImportJob.Status.PROCESSING,
                ImportJob.Status.SUCCEEDED,
            },
        )
        self.assertContains(response, "usage.csv")

    def test_analytics_workspace_surfaces_daily_and_ai_sections(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily Revenue")
        self.assertContains(response, "Order-Backed Financial Rows")
        self.assertContains(response, "Maintenance Summary")
        self.assertContains(response, "AI Supply Drafts")
