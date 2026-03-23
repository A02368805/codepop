from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from orders.models import (
    HubInventoryBalance,
    InventoryItem,
    Region,
    RegionAssignment,
    Store,
    StoreInventoryBalance,
    SupplyHub,
    InventorySnapshot,
)


class Command(BaseCommand):
    help = "Seed logistics dashboard demo data for one primary and one neighboring region"

    def handle(self, *args, **options):
        region_c, _ = Region.objects.get_or_create(code="REG-C", defaults={"name": "Region C"})
        region_b, _ = Region.objects.get_or_create(code="REG-B", defaults={"name": "Region B"})

        stores_c = []
        for i in range(1, 6):
            store, _ = Store.objects.get_or_create(name=f"Region C Store {i}", region=region_c)
            # Add demo coordinates (Region C stores in Chicago area)
            if not store.latitude:
                store.latitude = 41.8781 + (i * 0.01)
                store.longitude = -87.6298 + (i * 0.01)
                store.save(update_fields=["latitude", "longitude"])
            stores_c.append(store)

        for i in range(1, 3):
            store, _ = Store.objects.get_or_create(name=f"Region B Store {i}", region=region_b)
            # Add demo coordinates (Region B stores in Milwaukee area)
            if not store.latitude:
                store.latitude = 43.0381 + (i * 0.01)
                store.longitude = -87.9066 + (i * 0.01)
                store.save(update_fields=["latitude", "longitude"])

        stores_b = list(Store.objects.filter(region=region_b).order_by("name"))

        hub_c, _ = SupplyHub.objects.get_or_create(name="Region C Main Hub", region=region_c)
        if not hub_c.latitude:
            hub_c.latitude = 41.8781  # Chicago
            hub_c.longitude = -87.6298
            hub_c.save(update_fields=["latitude", "longitude"])

        hub_b, _ = SupplyHub.objects.get_or_create(name="Region B Support Hub", region=region_b)
        if not hub_b.latitude:
            hub_b.latitude = 43.0381  # Milwaukee
            hub_b.longitude = -87.9066
            hub_b.save(update_fields=["latitude", "longitude"])

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

        if stores_b:
            low_store = stores_b[0]
            StoreInventoryBalance.objects.update_or_create(
                store=low_store,
                item=vanilla,
                defaults={"quantity": 2, "threshold": 12},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=low_store,
                item=cherry,
                defaults={"quantity": 1, "threshold": 10},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=low_store,
                item=cola,
                defaults={"quantity": 3, "threshold": 18},
            )

        if len(stores_b) > 1:
            surplus_store = stores_b[1]
            StoreInventoryBalance.objects.update_or_create(
                store=surplus_store,
                item=vanilla,
                defaults={"quantity": 50, "threshold": 12},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=surplus_store,
                item=cherry,
                defaults={"quantity": 42, "threshold": 10},
            )
            StoreInventoryBalance.objects.update_or_create(
                store=surplus_store,
                item=cola,
                defaults={"quantity": 70, "threshold": 18},
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

        HubInventoryBalance.objects.update_or_create(
            hub=hub_b,
            item=vanilla,
            defaults={"quantity": 120},
        )
        HubInventoryBalance.objects.update_or_create(
            hub=hub_b,
            item=cherry,
            defaults={"quantity": 110},
        )
        HubInventoryBalance.objects.update_or_create(
            hub=hub_b,
            item=cola,
            defaults={"quantity": 150},
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

        RegionAssignment.objects.get_or_create(
            user=logistics_user,
            region=region_b,
            role="logistics_manager",
        )

        # Create inventory snapshots for trends demo (7-day depletion pattern)
        InventorySnapshot.objects.filter(created_at__gte=timezone.now() - timedelta(days=8)).delete()
        
        for day_offset in range(7, 0, -1):
            snapshot_time = timezone.now() - timedelta(days=day_offset)
            
            # Region B Store 1 (low-stock store) - show depletion trend
            if stores_b and len(stores_b) > 0:
                low_store = stores_b[0]
                qty_vanilla = max(2, 8 - day_offset)
                InventorySnapshot.objects.create(
                    store=low_store,
                    item=vanilla,
                    quantity=qty_vanilla,
                    threshold=12,
                    created_at=snapshot_time
                )
                qty_cherry = max(1, 6 - day_offset)
                InventorySnapshot.objects.create(
                    store=low_store,
                    item=cherry,
                    quantity=qty_cherry,
                    threshold=10,
                    created_at=snapshot_time
                )
            
            # Region B Store 2 (surplus store) - show growth trend
            if stores_b and len(stores_b) > 1:
                surplus_store = stores_b[1]
                qty_vanilla_s = 35 + (day_offset * 2)
                InventorySnapshot.objects.create(
                    store=surplus_store,
                    item=vanilla,
                    quantity=qty_vanilla_s,
                    threshold=12,
                    created_at=snapshot_time
                )

        self.stdout.write(self.style.SUCCESS("Logistics demo seed data ready."))
