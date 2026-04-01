import threading
from decimal import Decimal
from unittest.mock import patch

from apps.inventory.services import InventoryServiceError, get_store_balance
from apps.orders.models import Order
from apps.orders.services import (
    OrderServiceError,
    RefundEligibilityError,
    create_order,
    ensure_refund_allowed,
    transition_order_status,
)
from apps.payments.models import PaymentTransaction, RevenueLedgerEntry
from apps.payments.services import (
    record_payment_pending,
    record_payment_success,
    record_refund,
)
from apps.users.models import FavoriteDrink
from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from .helpers import make_inventory_item, make_region, make_store, make_user


class OrderWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.inventory_item = make_inventory_item(sku="SYRUP-STRAWBERRY")
        cls.cups = make_inventory_item(
            sku="CUPS-24OZ",
            name="24oz Cups",
            category="cups",
            threshold="100.00",
        )

        balance = get_store_balance(cls.store, cls.inventory_item)
        balance.on_hand_quantity = Decimal("12.00")
        balance.reorder_threshold = Decimal("4.00")
        balance.save()

        cup_balance = get_store_balance(cls.store, cls.cups)
        cup_balance.on_hand_quantity = Decimal("200.00")
        cup_balance.reorder_threshold = Decimal("50.00")
        cup_balance.save()

    def _create_order(self):
        return create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "large",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("1.00"),
                    "quantity": 2,
                    "customizations": {
                        "extras_total": "1.00",
                        "inventory_requirements": [
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "2.00"},
                            {"sku": "CUPS-24OZ", "quantity": "2.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )

    def test_order_lifecycle_reserves_inventory_and_sets_timestamps(self):
        order = self._create_order()
        self.assertEqual(order.status, Order.Status.PRICING_VALIDATED)

        record_payment_pending(order, payment_intent_id="pi_test_001")
        self.assertEqual(
            order.payment_transaction.status, PaymentTransaction.Status.PENDING
        )

        record_payment_success(
            order, payment_intent_id="pi_test_001", actor=self.customer
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(
                order=order, entry_type=RevenueLedgerEntry.EntryType.SALE
            ).count(),
            1,
        )

        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)
        transition_order_status(order, Order.Status.READY, actor=self.customer)
        transition_order_status(order, Order.Status.PICKED_UP, actor=self.customer)
        order.refresh_from_db()

        syrup_balance = get_store_balance(self.store, self.inventory_item)
        cup_balance = get_store_balance(self.store, self.cups)
        self.assertEqual(syrup_balance.on_hand_quantity, Decimal("10.00"))
        self.assertEqual(cup_balance.on_hand_quantity, Decimal("198.00"))
        self.assertEqual(order.status, Order.Status.PICKED_UP)
        self.assertIsNotNone(order.queued_at)
        self.assertIsNotNone(order.preparing_at)
        self.assertIsNotNone(order.ready_at)
        self.assertIsNotNone(order.picked_up_at)

    def test_refund_cutoff_blocks_customers_after_preparing(self):
        order = self._create_order()
        record_payment_pending(order, payment_intent_id="pi_test_002")
        record_payment_success(
            order, payment_intent_id="pi_test_002", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        with self.assertRaises(RefundEligibilityError):
            ensure_refund_allowed(order, actor=self.customer)

    def test_privileged_refund_override_allows_refund_after_preparing(self):
        order = self._create_order()
        record_payment_pending(order, payment_intent_id="pi_test_003")
        record_payment_success(
            order, payment_intent_id="pi_test_003", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)
        transition_order_status(order, Order.Status.PREPARING, actor=self.customer)

        payment = record_refund(
            order, actor=self.admin, notes="Admin override for store issue."
        )
        order.refresh_from_db()
        syrup_balance = get_store_balance(self.store, self.inventory_item)
        cup_balance = get_store_balance(self.store, self.cups)
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(order.refund_status, Order.RefundStatus.REFUNDED)
        self.assertEqual(payment.status, PaymentTransaction.Status.REFUNDED)
        self.assertEqual(syrup_balance.on_hand_quantity, Decimal("12.00"))
        self.assertEqual(cup_balance.on_hand_quantity, Decimal("200.00"))
        self.assertEqual(
            RevenueLedgerEntry.objects.filter(
                order=order, entry_type=RevenueLedgerEntry.EntryType.REFUND
            ).count(),
            1,
        )

    def test_queue_transition_blocks_when_inventory_is_insufficient(self):
        order = self._create_order()
        balance = get_store_balance(self.store, self.inventory_item)
        balance.on_hand_quantity = Decimal("1.00")
        balance.save(update_fields=["on_hand_quantity", "updated_at"])

        record_payment_pending(order, payment_intent_id="pi_test_004")
        record_payment_success(
            order, payment_intent_id="pi_test_004", actor=self.customer
        )

        with self.assertRaises(InventoryServiceError):
            transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)

    def test_create_order_rejects_items_from_different_store_snapshot(self):
        with self.assertRaises(OrderServiceError):
            create_order(
                store=self.store,
                customer=self.customer,
                items=[
                    {
                        "display_name": "Berry Burst",
                        "size": "large",
                        "base_price": Decimal("5.50"),
                        "extras_total": Decimal("1.00"),
                        "quantity": 1,
                        "store_code_snapshot": "OTHER-STORE",
                        "customizations": {
                            "extras_total": "1.00",
                            "inventory_requirements": [],
                        },
                    }
                ],
                actor=self.customer,
            )


class InventoryConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.region = make_region(code="C", name="Logan, UT")
        self.store = make_store(
            store_code="C001",
            region=self.region,
            name="Logan Main",
        )
        self.customer = make_user(
            email="concurrency@test.local",
            preferred_store=self.store,
            default_region=self.region,
        )
        self.inventory_item = make_inventory_item(sku="SYRUP-STRAWBERRY")

        balance = get_store_balance(self.store, self.inventory_item)
        balance.on_hand_quantity = Decimal("1.00")
        balance.reorder_threshold = Decimal("0.25")
        balance.save()

    def _create_paid_order(self):
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "large",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("1.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "1.00",
                        "inventory_requirements": [
                            {"sku": "SYRUP-STRAWBERRY", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )
        record_payment_pending(order, payment_intent_id=f"pi_{order.public_order_code}")
        record_payment_success(
            order,
            payment_intent_id=f"pi_{order.public_order_code}",
            actor=self.customer,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        return order

    def test_parallel_queue_transitions_do_not_oversubscribe_inventory(self):
        order_one = self._create_paid_order()
        order_two = self._create_paid_order()

        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def queue_order(order_id):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                local_order = Order.objects.get(pk=order_id)
                transition_order_status(
                    local_order,
                    Order.Status.QUEUED,
                    actor=self.customer,
                )
                with lock:
                    outcomes.append("queued")
            except InventoryServiceError:
                with lock:
                    outcomes.append("insufficient")
            finally:
                close_old_connections()
                connections.close_all()

        thread_one = threading.Thread(target=queue_order, args=(order_one.pk,))
        thread_two = threading.Thread(target=queue_order, args=(order_two.pk,))
        thread_one.start()
        thread_two.start()
        thread_one.join()
        thread_two.join()

        order_one.refresh_from_db()
        order_two.refresh_from_db()
        balance = get_store_balance(self.store, self.inventory_item)

        self.assertCountEqual(outcomes, ["queued", "insufficient"])
        self.assertEqual(balance.on_hand_quantity, Decimal("0.00"))
        self.assertCountEqual(
            [order_one.status, order_two.status],
            [Order.Status.QUEUED, Order.Status.PAID],
        )


class MenuAiAssistantViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="menu-ai@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    def test_menu_page_exposes_ai_launcher(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("orders:menu", args=[self.store.store_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask AI what to order")

    @patch("apps.orders.assistant._call_anthropic_menu_ai")
    def test_menu_ai_prompt_returns_menu_matches(self, mock_call):
        mock_call.return_value = {
            "title": "FloatStack Menu AI",
            "prompt": "I want something fruity and refreshing",
            "answer": "Start with Sprite or Lemon-Lime for a bright, refreshing build.",
            "quick_prompts": ["I want a creamy float"],
            "drink": {
                "name": "Citrus Sprite Twist",
                "recipe_key": "sprite",
                "size_snapshot": "medium",
                "base_price_snapshot": "2.95",
                "description": "A bright, refreshing drink built from the catalog.",
                "customizations_json": {
                    "schema_version": 1,
                    "menu_key": "sprite",
                    "recipe": {"name": "Citrus Sprite Twist"},
                },
            },
            "can_save": True,
            "menu_matches": [
                {
                    "slug": "sprite",
                    "name": "Sprite",
                    "description": "Bright and bubbly",
                    "reason": "Great bright citrus base.",
                }
            ],
            "uses_ai": True,
        }

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("orders:menu-ai", args=[self.store.store_code]),
            {"prompt": "I want something fruity and refreshing"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start with Sprite or Lemon-Lime")
        self.assertContains(response, "Customize")
        mock_call.assert_called_once()

    @patch("apps.orders.assistant._call_anthropic_menu_ai")
    def test_menu_ai_generated_drink_can_be_saved_to_favorites(self, mock_call):
        mock_call.return_value = {
            "title": "FloatStack Menu AI",
            "prompt": "I want something fruity and refreshing",
            "answer": "Start with Sprite or Lemon-Lime for a bright, refreshing build.",
            "quick_prompts": ["I want a creamy float"],
            "recipe": {
                "name": "Citrus Sprite Twist",
                "description": "A bright, refreshing drink built from the catalog.",
                "reason": "Built from existing ingredients to give you something new to try.",
                "base_soda": {
                    "slug": "sprite",
                    "label": "Sprite",
                },
                "syrups": [],
                "add_ins": [],
                "ice_cream": None,
                "starter_menu_item": {
                    "slug": "berry-burst",
                    "name": "Berry Burst",
                    "description": "Bright berry fizz with a crisp, easy-to-love finish.",
                },
            },
            "drink": {
                "name": "Citrus Sprite Twist",
                "recipe_key": "berry-burst",
                "size_snapshot": "medium",
                "base_price_snapshot": "2.95",
                "description": "A bright, refreshing drink built from the catalog.",
                "customizations_json": {
                    "schema_version": 1,
                    "source": "anthropic",
                    "ai_generated": True,
                    "menu_key": "berry-burst",
                    "recipe": {"name": "Citrus Sprite Twist"},
                },
            },
            "can_save": True,
            "menu_matches": [],
            "uses_ai": True,
        }

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("orders:menu-ai", args=[self.store.store_code]),
            {"prompt": "I want something fruity and refreshing"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New drink record")
        self.assertContains(response, "Save this drink")

        save_response = self.client.post(
            reverse("orders:menu-ai-save", args=[self.store.store_code]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertContains(save_response, "Saved to favorites")

        favorite = FavoriteDrink.objects.get(user=self.customer)
        self.assertTrue(favorite.customizations_json.get("ai_generated"))
        self.assertEqual(favorite.recipe_key, "berry-burst")
        self.assertEqual(favorite.size_snapshot, "medium")
        self.assertTrue(favorite.description)

    @patch("apps.orders.assistant._call_anthropic_menu_ai")
    def test_menu_ai_generated_drink_can_be_added_to_cart(self, mock_call):
        mock_call.return_value = {
            "title": "FloatStack Menu AI",
            "prompt": "I want something fruity and refreshing",
            "answer": "Start with a bright citrus base.",
            "quick_prompts": ["I want a creamy float"],
            "recipe": {
                "name": "Citrus Sprite Twist",
                "description": "A bright, refreshing drink built from the catalog.",
                "reason": "Built from existing ingredients.",
                "base_soda": {"slug": "sprite", "label": "Sprite"},
                "syrups": [],
                "add_ins": [],
                "ice_cream": None,
                "starter_menu_item": {
                    "slug": "berry-burst",
                    "name": "Berry Burst",
                    "description": "Bright berry fizz with a crisp, easy-to-love finish.",
                },
            },
            "drink": {
                "name": "Citrus Sprite Twist",
                "recipe_key": "berry-burst",
                "size_snapshot": "medium",
                "base_price_snapshot": "2.95",
                "extras_total": "0.00",
                "description": "A bright, refreshing drink built from the catalog.",
                "cart_item": {
                    "menu_key": "berry-burst",
                    "display_name": "Citrus Sprite Twist",
                    "size": "medium",
                    "base_price": "2.95",
                    "extras_total": "0.00",
                    "quantity": 1,
                    "description": "A bright, refreshing drink built from the catalog.",
                    "customizations": {
                        "soda": "sprite",
                        "syrups": [],
                        "add_ins": [],
                        "ice_cream": "",
                        "notes": "AI-generated",
                        "inventory_requirements": [],
                    },
                },
                "customizations_json": {
                    "schema_version": 1,
                    "source": "anthropic",
                    "ai_generated": True,
                    "menu_key": "berry-burst",
                    "recipe": {"name": "Citrus Sprite Twist"},
                },
            },
            "can_save": True,
            "menu_matches": [],
            "uses_ai": True,
        }

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("orders:menu-ai", args=[self.store.store_code]),
            {"prompt": "I want something fruity and refreshing"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Citrus Sprite Twist to cart")

        add_response = self.client.post(
            reverse("orders:menu-ai-add-to-cart", args=[self.store.store_code]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertContains(add_response, "Added to cart")

        session = self.client.session
        cart = session.get("codepop_cart", {})
        self.assertEqual(cart.get("store_code"), self.store.store_code)
        self.assertEqual(len(cart.get("items", [])), 1)
        self.assertEqual(cart["items"][0]["display_name"], "Citrus Sprite Twist")
