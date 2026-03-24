from django.core.management import call_command
from django.test import TestCase

from apps.imports.models import ImportJob
from apps.inventory.models import SupplySchedule
from apps.orders.models import Order
from apps.stores.models import Region, Store
from apps.supply_hubs.models import SupplyHub
from apps.users.models import User


class DemoSeedTests(TestCase):
    def test_bootstrap_demo_data_creates_expected_dataset(self):
        call_command("bootstrap_demo_data", reset=True, verbosity=0)

        self.assertEqual(Region.objects.count(), 7)
        self.assertEqual(SupplyHub.objects.count(), 7)
        self.assertEqual(Store.objects.filter(region__code="C").count(), 20)
        self.assertGreaterEqual(Store.objects.filter(region__code="F").count(), 5)
        self.assertGreaterEqual(Store.objects.filter(region__code="G").count(), 5)
        self.assertEqual(User.objects.filter(role=User.Role.LOGISTICS_MANAGER).count(), 7)
        self.assertGreaterEqual(User.objects.filter(role=User.Role.REPAIR_STAFF).count(), 3)
        self.assertEqual(Order.objects.filter(order_type=Order.OrderType.GUEST, customer__isnull=True).count(), 1)
        self.assertEqual(
            User.objects.filter(email="guest.lookup@floatstack.local").count(),
            0,
        )
        self.assertEqual(ImportJob.objects.filter(status=ImportJob.Status.SUCCEEDED).count(), 2)
        self.assertTrue(SupplySchedule.objects.filter(status=SupplySchedule.Status.APPROVED).exists())
