from decimal import Decimal

from apps.inventory.models import InventoryItem
from apps.inventory.services import get_store_balance, reserve_order_inventory
from apps.orders.models import Order, OrderItem
from apps.orders.services import create_order, transition_order_status
from apps.payments.services import record_payment_pending, record_payment_success
from django.test import TestCase
from tests.helpers import (
    assign_store,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


class InventoryDeductionQuantityTests(TestCase):
    """Tests for Bug 13: Inventory deduction not accounting for item quantity"""

    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

        # Create inventory items for a drink
        cls.diet_coke = make_inventory_item(
            sku="SODA-DIET-COKE",
            name="Diet Coke",
            category="soda",
        )
        cls.cherry_syrup = make_inventory_item(
            sku="SYRUP-CHERRY",
            name="Cherry Syrup",
            category="syrup",
        )
        cls.lime_syrup = make_inventory_item(
            sku="SYRUP-LIME",
            name="Lime Syrup",
            category="syrup",
        )
        cls.cups = make_inventory_item(
            sku="CUPS-24OZ",
            name="24oz Cups",
            category="cups",
        )

    def setUp(self):
        # Reset inventory balances for each test
        diet_coke_balance = get_store_balance(self.store, self.diet_coke)
        diet_coke_balance.on_hand_quantity = Decimal("100.00")
        diet_coke_balance.save()

        cherry_balance = get_store_balance(self.store, self.cherry_syrup)
        cherry_balance.on_hand_quantity = Decimal("100.00")
        cherry_balance.save()

        lime_balance = get_store_balance(self.store, self.lime_syrup)
        lime_balance.on_hand_quantity = Decimal("100.00")
        lime_balance.save()

        cups_balance = get_store_balance(self.store, self.cups)
        cups_balance.on_hand_quantity = Decimal("500.00")
        cups_balance.save()

    def test_inventory_deduction_with_multiple_quantity_same_drink(self):
        """
        Bug 13 Part 2: When customer adds multiple quantity of same drink to cart,
        only 1 of each ingredient is subtracted instead of the full quantity.

        If someone orders quantity=12 of the same drink:
        - Should deduct 12 cups, not 1
        - Should deduct 12 units of syrup, not 1
        """
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Diet Coke Cherry",
                    "size": "large",
                    "base_price": Decimal("5.00"),
                    "quantity": 12,  # Customer orders 12 of the same drink
                    "customizations": {
                        "inventory_requirements": [
                            {"sku": "SODA-DIET-COKE", "quantity": "1.00"},
                            {"sku": "SYRUP-CHERRY", "quantity": "1.00"},
                            {"sku": "CUPS-24OZ", "quantity": "1.00"},
                        ],
                    },
                }
            ],
            actor=self.customer,
        )

        # Move order to QUEUED to trigger inventory reservation
        record_payment_pending(order, payment_intent_id="pi_test_001")
        record_payment_success(
            order,
            payment_intent_id="pi_test_001",
            actor=self.customer,
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        # Check inventory deductions
        diet_coke_balance = get_store_balance(self.store, self.diet_coke)
        cherry_balance = get_store_balance(self.store, self.cherry_syrup)
        cups_balance = get_store_balance(self.store, self.cups)

        # Should deduct 12 of each item (quantity * requirement quantity)
        self.assertEqual(
            diet_coke_balance.on_hand_quantity,
            Decimal("88.00"),
            "Diet Coke should be reduced by 12 (quantity × 1.00 requirement)",
        )
        self.assertEqual(
            cherry_balance.on_hand_quantity,
            Decimal("88.00"),
            "Cherry syrup should be reduced by 12 (quantity × 1.00 requirement)",
        )
        self.assertEqual(
            cups_balance.on_hand_quantity,
            Decimal("488.00"),
            "Cups should be reduced by 12 (quantity × 1.00 requirement)",
        )

    def test_inventory_deduction_with_multiple_drinks_sharing_ingredient(self):
        """
        Bug 13 Part 1: When an order contains multiple drinks sharing a base ingredient,
        the supply level drops by the number of distinct drink types instead of total quantity.

        If order has:
        - 1 Diet Coke Cherry (needs 1 Diet Coke, 1 Cherry syrup)
        - 2 Diet Coke Lime (needs 2 Diet Coke, 2 Lime syrup)

        Total deduction should be:
        - Diet Coke: 1 + 2 = 3
        - Cherry syrup: 1
        - Lime syrup: 2
        """
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Diet Coke Cherry",
                    "size": "large",
                    "base_price": Decimal("5.00"),
                    "quantity": 1,
                    "customizations": {
                        "inventory_requirements": [
                            {"sku": "SODA-DIET-COKE", "quantity": "1.00"},
                            {"sku": "SYRUP-CHERRY", "quantity": "1.00"},
                            {"sku": "CUPS-24OZ", "quantity": "1.00"},
                        ],
                    },
                },
                {
                    "display_name": "Diet Coke Lime",
                    "size": "large",
                    "base_price": Decimal("5.00"),
                    "quantity": 2,  # 2 of this drink
                    "customizations": {
                        "inventory_requirements": [
                            {"sku": "SODA-DIET-COKE", "quantity": "1.00"},
                            {"sku": "SYRUP-LIME", "quantity": "1.00"},
                            {"sku": "CUPS-24OZ", "quantity": "1.00"},
                        ],
                    },
                },
            ],
            actor=self.customer,
        )

        # Move order to QUEUED to trigger inventory reservation
        record_payment_pending(order, payment_intent_id="pi_test_002")
        record_payment_success(
            order,
            payment_intent_id="pi_test_002",
            actor=self.customer,
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        # Check inventory deductions
        diet_coke_balance = get_store_balance(self.store, self.diet_coke)
        cherry_balance = get_store_balance(self.store, self.cherry_syrup)
        lime_balance = get_store_balance(self.store, self.lime_syrup)
        cups_balance = get_store_balance(self.store, self.cups)

        # Diet Coke should be reduced by 3 total (1 from cherry drink + 2 from lime drink)
        self.assertEqual(
            diet_coke_balance.on_hand_quantity,
            Decimal("97.00"),
            "Diet Coke should be reduced by 3 (1 + 2 = 3 total quantity)",
        )
        # Cherry syrup: 1 quantity × 1.00 requirement = 1
        self.assertEqual(
            cherry_balance.on_hand_quantity,
            Decimal("99.00"),
            "Cherry syrup should be reduced by 1 (quantity 1 × requirement 1.00)",
        )
        # Lime syrup: 2 quantity × 1.00 requirement = 2
        self.assertEqual(
            lime_balance.on_hand_quantity,
            Decimal("98.00"),
            "Lime syrup should be reduced by 2 (quantity 2 × requirement 1.00)",
        )
        # Cups: (1 + 2) × 1.00 requirement = 3
        self.assertEqual(
            cups_balance.on_hand_quantity,
            Decimal("497.00"),
            "Cups should be reduced by 3 (1 + 2 = 3 total quantity)",
        )
