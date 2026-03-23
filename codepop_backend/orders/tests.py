from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import (
	HubInventoryBalance,
	InventoryItem,
	Region,
	RegionAssignment,
	Store,
	StoreInventoryBalance,
	SupplyHub,
	SupplyTransfer,
)


class LogisticsDashboardTests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="lm", password="testpass123")
		self.token = Token.objects.create(user=self.user)
		self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

		self.region = Region.objects.create(name="Region C", code="REG-C")
		self.other_region = Region.objects.create(name="Region B", code="REG-B")
		RegionAssignment.objects.create(user=self.user, region=self.region, role="logistics_manager")

		self.store_a = Store.objects.create(name="Store A", region=self.region)
		self.store_b = Store.objects.create(name="Store B", region=self.region)
		self.other_store = Store.objects.create(name="Store X", region=self.other_region)
		self.hub = SupplyHub.objects.create(name="Hub C", region=self.region)
		self.item = InventoryItem.objects.create(name="Vanilla Syrup", item_type="syrup", unit="liters")

		self.source_balance = HubInventoryBalance.objects.create(hub=self.hub, item=self.item, quantity=100)
		self.destination_balance = StoreInventoryBalance.objects.create(
			store=self.store_b,
			item=self.item,
			quantity=3,
			threshold=5,
		)

	def test_dashboard_denies_unassigned_region(self):
		response = self.client.get(reverse("orders:logistics-dashboard-api", args=[self.other_region.id]))
		self.assertEqual(response.status_code, 403)

	def test_transfer_complete_updates_balances(self):
		create_response = self.client.post(
			reverse("orders:logistics-transfer-create"),
			{
				"source_hub_id": self.hub.id,
				"destination_store_id": self.store_b.id,
				"item_id": self.item.id,
				"quantity": 10,
				"note": "test transfer",
			},
			format="json",
		)
		self.assertEqual(create_response.status_code, 201)
		transfer_id = create_response.data["id"]

		approve_response = self.client.post(
			reverse("orders:logistics-transfer-status", args=[transfer_id, "approve"]),
			format="json",
		)
		self.assertEqual(approve_response.status_code, 200)

		complete_response = self.client.post(
			reverse("orders:logistics-transfer-status", args=[transfer_id, "complete"]),
			format="json",
		)
		self.assertEqual(complete_response.status_code, 200)

		self.source_balance.refresh_from_db()
		self.destination_balance.refresh_from_db()
		transfer = SupplyTransfer.objects.get(id=transfer_id)

		self.assertEqual(self.source_balance.quantity, 90)
		self.assertEqual(self.destination_balance.quantity, 13)
		self.assertEqual(transfer.status, "completed")
