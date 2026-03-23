from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from orders.models import (
    HubInventoryBalance,
    InventoryItem,
    Region,
    RegionAssignment,
    RestockAlert,
    Store,
    StoreInventoryBalance,
    SupplyHub,
    SupplyTransfer,
    InventorySnapshot,
)


class Command(BaseCommand):
    help = "Seed multi-region logistics demo data with distinct scenarios"

    def _upsert_store(self, region, name, latitude, longitude):
        store, _ = Store.objects.get_or_create(name=name, region=region)
        store.latitude = latitude
        store.longitude = longitude
        store.save(update_fields=["latitude", "longitude"])
        return store

    def _upsert_hub(self, region, name, latitude, longitude):
        hub, _ = SupplyHub.objects.get_or_create(name=name, region=region)
        hub.latitude = latitude
        hub.longitude = longitude
        hub.save(update_fields=["latitude", "longitude"])
        return hub

    def _set_store_balance(self, store, item, quantity, threshold):
        StoreInventoryBalance.objects.update_or_create(
            store=store,
            item=item,
            defaults={"quantity": quantity, "threshold": threshold},
        )

    def _set_hub_balance(self, hub, item, quantity):
        HubInventoryBalance.objects.update_or_create(
            hub=hub,
            item=item,
            defaults={"quantity": quantity},
        )

    def _seed_snapshots(self, store, item, threshold, quantities):
        now = timezone.now()
        for offset, qty in enumerate(quantities[::-1], start=1):
            InventorySnapshot.objects.create(
                store=store,
                item=item,
                quantity=qty,
                threshold=threshold,
                created_at=now - timedelta(days=offset),
            )

    def handle(self, *args, **options):
        region_c, _ = Region.objects.get_or_create(code="REG-C", defaults={"name": "Region C - Balanced Ops"})
        region_b, _ = Region.objects.get_or_create(code="REG-B", defaults={"name": "Region B - Shortage Pressure"})
        region_d, _ = Region.objects.get_or_create(code="REG-D", defaults={"name": "Region D - Transfer Heavy"})
        region_e, _ = Region.objects.get_or_create(code="REG-E", defaults={"name": "Region E - Healthy Buffer"})

        seeded_regions = [region_b, region_c, region_d, region_e]

        # Keep region names deterministic
        region_c.name = "Region C - Balanced Ops"
        region_b.name = "Region B - Shortage Pressure"
        region_d.name = "Region D - Transfer Heavy"
        region_e.name = "Region E - Healthy Buffer"
        Region.objects.bulk_update([region_b, region_c, region_d, region_e], ["name"])

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
        lime, _ = InventoryItem.objects.get_or_create(
            name="Lime Add-In",
            item_type="addin",
            defaults={"unit": "units"},
        )

        # Clear non-idempotent historical/demo records for seeded regions
        RestockAlert.objects.filter(store__region__in=seeded_regions).delete()
        SupplyTransfer.objects.filter(
            Q(destination_store__region__in=seeded_regions)
            | Q(source_store__region__in=seeded_regions)
            | Q(source_hub__region__in=seeded_regions)
        ).delete()
        InventorySnapshot.objects.filter(store__region__in=seeded_regions).delete()

        # Region B: one low-stock store + one surplus store (best for recommendations and stockout alerts)
        b1 = self._upsert_store(region_b, "Region B Store 1", 43.0470, -87.9000)
        b2 = self._upsert_store(region_b, "Region B Store 2", 43.0610, -87.9220)
        b_hub = self._upsert_hub(region_b, "Region B Support Hub", 43.0381, -87.9066)

        self._set_store_balance(b1, vanilla, 2, 12)
        self._set_store_balance(b1, cherry, 1, 10)
        self._set_store_balance(b1, cola, 3, 18)
        self._set_store_balance(b1, lime, 4, 15)

        self._set_store_balance(b2, vanilla, 50, 12)
        self._set_store_balance(b2, cherry, 42, 10)
        self._set_store_balance(b2, cola, 70, 18)
        self._set_store_balance(b2, lime, 38, 15)

        self._set_hub_balance(b_hub, vanilla, 120)
        self._set_hub_balance(b_hub, cherry, 110)
        self._set_hub_balance(b_hub, cola, 150)
        self._set_hub_balance(b_hub, lime, 95)

        RestockAlert.objects.create(
            store=b1,
            item=vanilla,
            status="open",
            severity="critical",
            message="Vanilla Syrup critically low at Region B Store 1",
        )
        RestockAlert.objects.create(
            store=b1,
            item=cherry,
            status="open",
            severity="critical",
            message="Cherry Syrup critically low at Region B Store 1",
        )

        # Region C: balanced operations with broad inventory coverage
        c_hub = self._upsert_hub(region_c, "Region C Main Hub", 41.8781, -87.6298)
        stores_c = [
            self._upsert_store(region_c, "Region C Store 1", 41.8850, -87.6200),
            self._upsert_store(region_c, "Region C Store 2", 41.8650, -87.6400),
            self._upsert_store(region_c, "Region C Store 3", 41.9010, -87.6480),
            self._upsert_store(region_c, "Region C Store 4", 41.8460, -87.6120),
            self._upsert_store(region_c, "Region C Store 5", 41.8330, -87.6700),
        ]

        for idx, store in enumerate(stores_c, start=1):
            self._set_store_balance(store, vanilla, 36 - idx * 4, 14)
            self._set_store_balance(store, cherry, 30 - idx * 3, 12)
            self._set_store_balance(store, cola, 65 - idx * 5, 24)
            self._set_store_balance(store, lime, 28 - idx * 2, 12)

        self._set_hub_balance(c_hub, vanilla, 500)
        self._set_hub_balance(c_hub, cherry, 450)
        self._set_hub_balance(c_hub, cola, 900)
        self._set_hub_balance(c_hub, lime, 300)

        RestockAlert.objects.create(
            store=stores_c[-1],
            item=cola,
            status="open",
            severity="low",
            message="Cola Base is nearing threshold in Region C Store 5",
        )

        # Region D: transfer-heavy, mixed route quality and active workflows
        d_hub = self._upsert_hub(region_d, "Region D Central Hub", 32.7767, -96.7970)
        d1 = self._upsert_store(region_d, "Region D Downtown", 32.7900, -96.8000)
        d2 = self._upsert_store(region_d, "Region D North", 32.9350, -96.7600)
        d3 = self._upsert_store(region_d, "Region D Remote", 33.1100, -96.6200)

        self._set_store_balance(d1, vanilla, 4, 14)
        self._set_store_balance(d1, cherry, 5, 14)
        self._set_store_balance(d1, cola, 2, 22)
        self._set_store_balance(d1, lime, 6, 12)

        self._set_store_balance(d2, vanilla, 58, 14)
        self._set_store_balance(d2, cherry, 52, 14)
        self._set_store_balance(d2, cola, 80, 22)
        self._set_store_balance(d2, lime, 40, 12)

        self._set_store_balance(d3, vanilla, 18, 14)
        self._set_store_balance(d3, cherry, 15, 14)
        self._set_store_balance(d3, cola, 14, 22)
        self._set_store_balance(d3, lime, 9, 12)

        self._set_hub_balance(d_hub, vanilla, 260)
        self._set_hub_balance(d_hub, cherry, 240)
        self._set_hub_balance(d_hub, cola, 420)
        self._set_hub_balance(d_hub, lime, 180)

        RestockAlert.objects.create(
            store=d1,
            item=cola,
            status="open",
            severity="critical",
            message="Cola Base critically low at Region D Downtown",
        )

        # Region E: healthy buffer, minimal risk signals
        e_hub = self._upsert_hub(region_e, "Region E Coastal Hub", 47.6062, -122.3321)
        e1 = self._upsert_store(region_e, "Region E Store 1", 47.6200, -122.3400)
        e2 = self._upsert_store(region_e, "Region E Store 2", 47.5800, -122.3000)
        e3 = self._upsert_store(region_e, "Region E Store 3", 47.6400, -122.2800)

        for store, vanilla_qty, cherry_qty, cola_qty, lime_qty in [
            (e1, 42, 35, 85, 28),
            (e2, 39, 32, 78, 24),
            (e3, 45, 38, 88, 30),
        ]:
            self._set_store_balance(store, vanilla, vanilla_qty, 16)
            self._set_store_balance(store, cherry, cherry_qty, 14)
            self._set_store_balance(store, cola, cola_qty, 26)
            self._set_store_balance(store, lime, lime_qty, 14)

        self._set_hub_balance(e_hub, vanilla, 280)
        self._set_hub_balance(e_hub, cherry, 230)
        self._set_hub_balance(e_hub, cola, 510)
        self._set_hub_balance(e_hub, lime, 210)

        logistics_user, created = User.objects.get_or_create(
            username="logistics_demo",
            defaults={"email": "logistics_demo@example.com", "is_staff": True},
        )
        if created:
            logistics_user.set_password("demo12345")
            logistics_user.save(update_fields=["password"])
        if not logistics_user.is_staff:
            logistics_user.is_staff = True
            logistics_user.save(update_fields=["is_staff"])

        # Assign demo user to all seeded regions
        for region in seeded_regions:
            RegionAssignment.objects.get_or_create(
                user=logistics_user,
                region=region,
                role="logistics_manager",
            )

        # Seed transfers to showcase workflow states
        SupplyTransfer.objects.create(
            source_store=b2,
            destination_store=b1,
            item=vanilla,
            quantity=15,
            status="pending",
            requested_by=logistics_user,
            note="Auto-seeded: rebalance shortage in Region B",
        )
        SupplyTransfer.objects.create(
            source_hub=b_hub,
            destination_store=b1,
            item=cola,
            quantity=20,
            status="approved",
            requested_by=logistics_user,
            approved_by=logistics_user,
            approved_at=timezone.now() - timedelta(hours=2),
            note="Auto-seeded: urgent cola replenishment",
        )
        SupplyTransfer.objects.create(
            source_store=d2,
            destination_store=d1,
            item=cherry,
            quantity=18,
            status="pending",
            requested_by=logistics_user,
            note="Auto-seeded: active transfer queue in Region D",
        )
        SupplyTransfer.objects.create(
            source_hub=d_hub,
            destination_store=d3,
            item=lime,
            quantity=16,
            status="approved",
            requested_by=logistics_user,
            approved_by=logistics_user,
            approved_at=timezone.now() - timedelta(hours=5),
            note="Auto-seeded: approved long-route replenishment",
        )

        # Seed 7-day trend snapshots with different patterns by region
        self._seed_snapshots(b1, vanilla, 12, [12, 10, 9, 8, 6, 4, 2])
        self._seed_snapshots(b2, vanilla, 12, [32, 35, 37, 40, 43, 46, 50])

        self._seed_snapshots(stores_c[0], cola, 24, [72, 71, 70, 69, 68, 67, 66])
        self._seed_snapshots(stores_c[-1], cola, 24, [36, 34, 32, 28, 24, 20, 15])

        self._seed_snapshots(d1, cola, 22, [18, 16, 14, 12, 9, 6, 2])
        self._seed_snapshots(d2, cherry, 14, [28, 32, 36, 40, 44, 48, 52])

        self._seed_snapshots(e1, vanilla, 16, [38, 39, 40, 41, 41, 42, 42])
        self._seed_snapshots(e2, cola, 26, [76, 77, 77, 78, 78, 79, 79])

        self.stdout.write(self.style.SUCCESS("Logistics demo seed data ready for regions: REG-B, REG-C, REG-D, REG-E."))
