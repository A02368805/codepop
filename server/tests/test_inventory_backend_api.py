import json
from decimal import Decimal

from apps.inventory.services import get_store_balance
from django.test import TestCase
from django.urls import reverse

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


class InventoryBackendApiPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.item = make_inventory_item(
            sku="SYRUP-BACKEND-TEST",
            name="Backend Test Syrup",
            threshold="6.00",
        )
        cls.balance = get_store_balance(cls.store, cls.item)
        cls.balance.on_hand_quantity = Decimal("12.00")
        cls.balance.reorder_threshold = Decimal("6.00")
        cls.balance.save()

        cls.manager = make_user(
            email="manager-inventory-backend@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.manager, cls.store)

        cls.admin = make_user(
            email="admin-inventory-backend@test.local",
            role="admin",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.admin, cls.store)

        cls.logistics = make_user(
            email="logistics-inventory-backend@test.local",
            role="logistics_manager",
            default_region=cls.region,
        )
        assign_region(cls.logistics, cls.region)

        cls.account_user = make_user(
            email="account-inventory-backend@test.local",
            role="account_user",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    def setUp(self):
        self.balance.on_hand_quantity = Decimal("12.00")
        self.balance.reorder_threshold = Decimal("6.00")
        self.balance.save(update_fields=["on_hand_quantity", "reorder_threshold"])
        self.report_url = reverse("inventory_api:report")
        self.update_url = reverse("inventory_api:update", args=[self.balance.id])

    def test_anonymous_report_access_is_denied(self):
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication required.")

    def test_anonymous_patch_is_denied_and_does_not_mutate(self):
        response = self.client.patch(
            self.update_url,
            data=json.dumps({"used_quantity": "1.00"}),
            content_type="application/json",
        )

        self.balance.refresh_from_db()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication required.")
        self.assertEqual(self.balance.on_hand_quantity, Decimal("12.00"))

    def test_unprivileged_account_user_is_denied_for_report_and_patch(self):
        self.client.force_login(self.account_user)

        report_response = self.client.get(self.report_url)
        patch_response = self.client.patch(
            self.update_url,
            data=json.dumps({"used_quantity": "1.00"}),
            content_type="application/json",
        )

        self.balance.refresh_from_db()
        self.assertEqual(report_response.status_code, 403)
        self.assertEqual(patch_response.status_code, 403)
        self.assertEqual(self.balance.on_hand_quantity, Decimal("12.00"))

    def test_manager_and_admin_can_use_report_and_patch(self):
        for privileged_user in (self.manager, self.admin):
            with self.subTest(role=privileged_user.role):
                self.balance.on_hand_quantity = Decimal("12.00")
                self.balance.save(update_fields=["on_hand_quantity"])
                self.client.force_login(privileged_user)

                report_response = self.client.get(self.report_url)
                self.assertEqual(report_response.status_code, 200)
                report_payload = report_response.json()
                self.assertIn("inventory_items", report_payload)
                self.assertEqual(report_payload["total_items"], 1)

                patch_response = self.client.patch(
                    self.update_url,
                    data=json.dumps({"used_quantity": "1.50"}),
                    content_type="application/json",
                )
                self.assertEqual(patch_response.status_code, 200)
                self.balance.refresh_from_db()
                self.assertEqual(self.balance.on_hand_quantity, Decimal("10.50"))

    def test_logistics_manager_can_read_report_but_cannot_patch(self):
        self.client.force_login(self.logistics)

        report_response = self.client.get(self.report_url)
        patch_response = self.client.patch(
            self.update_url,
            data=json.dumps({"used_quantity": "1.00"}),
            content_type="application/json",
        )

        self.balance.refresh_from_db()
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(patch_response.status_code, 403)
        self.assertEqual(self.balance.on_hand_quantity, Decimal("12.00"))
