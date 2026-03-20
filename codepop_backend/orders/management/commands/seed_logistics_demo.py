from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from orders.models import (
    HubInventoryBalance,
    InventoryItem,
    Region,
    RegionAssignment,
    Store,
    StoreInventoryBalance,
    SupplyHub,
)


class Command(BaseCommand):
    help = "Seed logistics dashboard demo data for one primary and one neighboring region"

    def handle(self, *args, **options):
        region_c, _ = Region.objects.get_or_create(code="REG-C", defaults={"name": "Region C"})
        region_b, _ = Region.objects.get_or_create(code="REG-B", defaults={"name": "Region B"})

        stores_c = []
        for i in range(1, 6):
            store, _ = Store.objects.get_or_create(name=f"Region C Store {i}", region=region_c)
            stores_c.append(store)

        for i in range(1, 3):
            Store.objects.get_or_create(name=f"Region B Store {i}", region=region_b)

        hub_c, _ = SupplyHub.objects.get_or_create(name="Region C Main Hub", region=region_c)

        vanilla, _ = InventoryItem.objects.get_or_create(
            name="Vanilla Syrup",
            item_type="syrup",
            defaults={"unit": "liters"},
        )
        cherry, _ = InventoryItem.objects.get_or_create(
            name="Cherry Syrup",
            item_type="syrup",
            defaults={"unit": "liters"},
        )
        cola, _ = InventoryItem.objects.get_or_create(
            name="Cola Base",
            item_type="soda",
            defaults={"unit": "liters"},
        )

        for idx, store in enumerate(stores_c):
            StoreInventoryBalance.objects.update_or_create(
                store=store,
                item=vanilla,
                defaults={"quantity": max(2, 30 - idx * 7), "threshold": 10},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=store,
                item=cherry,
                defaults={"quantity": max(3, 28 - idx * 6), "threshold": 9},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=store,
                item=cola,
                defaults={"quantity": max(5, 60 - idx * 8), "threshold": 20},
            )

        HubInventoryBalance.objects.update_or_create(
            hub=hub_c,
            item=vanilla,
            defaults={"quantity": 500},
        )
        HubInventoryBalance.objects.update_or_create(
            hub=hub_c,
            item=cherry,
            defaults={"quantity": 450},
        )
        HubInventoryBalance.objects.update_or_create(
            hub=hub_c,
            item=cola,
            defaults={"quantity": 900},
        )

        logistics_user, created = User.objects.get_or_create(
            username="logistics_demo",
            defaults={"email": "logistics_demo@example.com", "is_staff": True},
        )
        if created:
            logistics_user.set_password("demo12345")
            logistics_user.save(update_fields=["password"])

        RegionAssignment.objects.get_or_create(
            user=logistics_user,
            region=region_c,
            role="logistics_manager",
        )

        self.stdout.write(self.style.SUCCESS("Logistics demo seed data ready."))
