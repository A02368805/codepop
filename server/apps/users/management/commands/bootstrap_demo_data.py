import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from apps.imports.models import ImportJob
from apps.imports.services import import_repair_status_csv, import_supply_usage_csv
from apps.inventory.models import (
    InventoryItem,
    LocalSupplier,
    RestockAlert,
    StoreInventoryBalance,
    SupplierReplenishment,
    SupplySchedule,
    SupplyUsageRecord,
)
from apps.inventory.services import (
    approve_supply_schedule,
    approve_transfer,
    deliver_transfer,
    evaluate_restock_alert,
    get_hub_balance,
    get_store_balance,
    receive_transfer,
    request_transfer,
    reserve_transfer_inventory,
    ship_transfer,
)
from apps.maintenance.models import (
    Machine,
    MachineStatusEvent,
    MachineType,
    MaintenancePolicy,
    RepairAssignment,
)
from apps.maintenance.services import (
    append_machine_status_event,
    create_repair_assignment,
    evaluate_warning_escalation,
)
from apps.notifications.models import Notification
from apps.orders.catalog import build_cart_item, catalog_inventory_definitions
from apps.orders.models import Order
from apps.orders.services import create_order, transition_order_status
from apps.payments.models import PaymentTransaction, RevenueLedgerEntry
from apps.payments.services import (
    record_payment_pending,
    record_payment_success,
    record_refund,
)
from apps.stores.models import Region, Store
from apps.supply_hubs.models import HubInventoryBalance, SupplyHub, SupplyTransfer
from apps.sync.models import AuditLog, SyncOutboxEvent
from apps.users.models import User, UserRegionAssignment, UserStoreAssignment
from apps.users.services import save_favorite_drink, save_preference_profile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

REGION_DEFINITIONS = {
    "A": {
        "name": "Chicago, IL",
        "hub_city": "Chicago",
        "hub_state_code": "IL",
        "latitude": "41.878113",
        "longitude": "-87.629799",
    },
    "B": {
        "name": "New Jersey / New York",
        "hub_city": "Jersey City",
        "hub_state_code": "NJ",
        "latitude": "40.717754",
        "longitude": "-74.043143",
    },
    "C": {
        "name": "Logan, UT",
        "hub_city": "Logan",
        "hub_state_code": "UT",
        "latitude": "41.736980",
        "longitude": "-111.833836",
    },
    "D": {
        "name": "Dallas, TX",
        "hub_city": "Dallas",
        "hub_state_code": "TX",
        "latitude": "32.776665",
        "longitude": "-96.796989",
    },
    "E": {
        "name": "Atlanta, GA",
        "hub_city": "Atlanta",
        "hub_state_code": "GA",
        "latitude": "33.749001",
        "longitude": "-84.387978",
    },
    "F": {
        "name": "Phoenix, AZ",
        "hub_city": "Phoenix",
        "hub_state_code": "AZ",
        "latitude": "33.448376",
        "longitude": "-112.074036",
    },
    "G": {
        "name": "Boise, ID",
        "hub_city": "Boise",
        "hub_state_code": "ID",
        "latitude": "43.615021",
        "longitude": "-116.202316",
    },
}

STORE_DEFINITIONS = {
    "A": [
        (
            "A001",
            "Chicago Loop",
            "Chicago",
            "IL",
            "120 W Lake St",
            "60601",
            "41.885311",
            "-87.631779",
        ),
        (
            "A002",
            "Evanston North",
            "Evanston",
            "IL",
            "807 Church St",
            "60201",
            "42.048213",
            "-87.683303",
        ),
    ],
    "B": [
        (
            "B001",
            "Jersey City Exchange",
            "Jersey City",
            "NJ",
            "30 Hudson St",
            "07302",
            "40.719446",
            "-74.034166",
        ),
        (
            "B002",
            "Newark Broad",
            "Newark",
            "NJ",
            "744 Broad St",
            "07102",
            "40.735657",
            "-74.172366",
        ),
    ],
    "C": [
        (
            "C001",
            "Logan Main",
            "Logan",
            "UT",
            "123 Main St",
            "84321",
            "41.736980",
            "-111.833836",
        ),
        (
            "C002",
            "North Logan Canyon",
            "North Logan",
            "UT",
            "456 Canyon Rd",
            "84341",
            "41.769089",
            "-111.804093",
        ),
        (
            "C003",
            "Providence Riverwoods",
            "Providence",
            "UT",
            "112 Riverwoods Pkwy",
            "84332",
            "41.704611",
            "-111.817970",
        ),
        (
            "C004",
            "Smithfield Center",
            "Smithfield",
            "UT",
            "77 Center St",
            "84335",
            "41.838265",
            "-111.832178",
        ),
        (
            "C005",
            "Brigham City Forest",
            "Brigham City",
            "UT",
            "15 Forest St",
            "84302",
            "41.510217",
            "-112.015502",
        ),
        (
            "C006",
            "Ogden Riverdale",
            "Ogden",
            "UT",
            "401 24th St",
            "84401",
            "41.223000",
            "-111.973830",
        ),
        (
            "C007",
            "Layton East",
            "Layton",
            "UT",
            "520 Hill Field Rd",
            "84041",
            "41.060221",
            "-111.971053",
        ),
        (
            "C008",
            "Bountiful South",
            "Bountiful",
            "UT",
            "75 Orchard Dr",
            "84010",
            "40.889389",
            "-111.880771",
        ),
        (
            "C009",
            "Salt Lake Downtown",
            "Salt Lake City",
            "UT",
            "210 State St",
            "84111",
            "40.762761",
            "-111.887985",
        ),
        (
            "C010",
            "Murray Central",
            "Murray",
            "UT",
            "95 Vine St",
            "84107",
            "40.658565",
            "-111.888274",
        ),
        (
            "C011",
            "Sandy Alta",
            "Sandy",
            "UT",
            "150 10600 S",
            "84070",
            "40.558908",
            "-111.890801",
        ),
        (
            "C012",
            "Draper Peaks",
            "Draper",
            "UT",
            "390 12300 S",
            "84020",
            "40.526133",
            "-111.863823",
        ),
        (
            "C013",
            "Lehi Tech",
            "Lehi",
            "UT",
            "260 Aspen Ave",
            "84043",
            "40.391617",
            "-111.850766",
        ),
        (
            "C014",
            "American Fork Main",
            "American Fork",
            "UT",
            "90 Main St",
            "84003",
            "40.376897",
            "-111.795764",
        ),
        (
            "C015",
            "Orem University",
            "Orem",
            "UT",
            "760 State St",
            "84058",
            "40.296898",
            "-111.694648",
        ),
        (
            "C016",
            "Provo Center",
            "Provo",
            "UT",
            "42 University Ave",
            "84601",
            "40.233844",
            "-111.658534",
        ),
        (
            "C017",
            "Spanish Fork Canyon",
            "Spanish Fork",
            "UT",
            "150 800 N",
            "84660",
            "40.114955",
            "-111.654923",
        ),
        (
            "C018",
            "Heber Valley",
            "Heber City",
            "UT",
            "345 Main St",
            "84032",
            "40.507008",
            "-111.413798",
        ),
        (
            "C019",
            "Park City Summit",
            "Park City",
            "UT",
            "675 Park Ave",
            "84060",
            "40.646063",
            "-111.498014",
        ),
        (
            "C020",
            "Tooele Gateway",
            "Tooele",
            "UT",
            "980 Main St",
            "84074",
            "40.530777",
            "-112.298279",
        ),
    ],
    "D": [
        (
            "D001",
            "Dallas North",
            "Dallas",
            "TX",
            "410 Elm St",
            "75201",
            "32.781609",
            "-96.800473",
        ),
        (
            "D002",
            "Plano Legacy",
            "Plano",
            "TX",
            "7600 Windrose Ave",
            "75024",
            "33.077904",
            "-96.821254",
        ),
    ],
    "E": [
        (
            "E001",
            "Atlanta Midtown",
            "Atlanta",
            "GA",
            "999 Peachtree St",
            "30309",
            "33.781334",
            "-84.383108",
        ),
        (
            "E002",
            "Marietta Square",
            "Marietta",
            "GA",
            "11 North Park Sq",
            "30060",
            "33.952602",
            "-84.549932",
        ),
    ],
    "F": [
        (
            "F001",
            "Phoenix Central",
            "Phoenix",
            "AZ",
            "240 Camelback Rd",
            "85012",
            "33.509540",
            "-112.070427",
        ),
        (
            "F002",
            "Mesa Gateway",
            "Mesa",
            "AZ",
            "180 Main St",
            "85201",
            "33.415184",
            "-111.831473",
        ),
        (
            "F003",
            "Tempe Lakes",
            "Tempe",
            "AZ",
            "99 Mill Ave",
            "85281",
            "33.430569",
            "-111.939627",
        ),
        (
            "F004",
            "Chandler Square",
            "Chandler",
            "AZ",
            "140 Arizona Ave",
            "85225",
            "33.303202",
            "-111.841250",
        ),
        (
            "F005",
            "Gilbert Ranch",
            "Gilbert",
            "AZ",
            "75 Guadalupe Rd",
            "85233",
            "33.362821",
            "-111.789028",
        ),
    ],
    "G": [
        (
            "G001",
            "Boise Capitol",
            "Boise",
            "ID",
            "50 Idaho St",
            "83702",
            "43.615018",
            "-116.202313",
        ),
        (
            "G002",
            "Meridian Village",
            "Meridian",
            "ID",
            "110 Main St",
            "83642",
            "43.612109",
            "-116.391513",
        ),
        (
            "G003",
            "Nampa Market",
            "Nampa",
            "ID",
            "215 12th Ave",
            "83651",
            "43.540718",
            "-116.563462",
        ),
        (
            "G004",
            "Caldwell Riverfront",
            "Caldwell",
            "ID",
            "88 Dearborn St",
            "83605",
            "43.662938",
            "-116.687359",
        ),
        (
            "G005",
            "Eagle Foothills",
            "Eagle",
            "ID",
            "170 State St",
            "83616",
            "43.695442",
            "-116.354434",
        ),
    ],
}

MACHINE_TYPE_DEFINITIONS = [
    ("MIXER_A", "Primary Mixer", 45, 3, 1),
    ("CARBONATOR_X", "Carbonator", 30, 2, 1),
    ("FREEZER_SOFTSERVE", "Soft Serve Freezer", 21, 1, 1),
]

PRIMARY_STORE_CODES = ["A001", "B001", "C001", "D001", "E001", "F001", "G001", "C002"]
REPAIR_ASSIGNMENTS = {
    "repair.north": ["C001", "C002", "C003", "C004", "C005", "C006", "C007"],
    "repair.metro": ["C008", "C009", "C010", "C011", "C012", "C013", "C014"],
    "repair.south": ["C015", "C016", "C017", "C018", "C019", "C020"],
}


class Command(BaseCommand):
    help = "Bootstraps prompt-2 demo data for the Django-first FloatStack architecture."

    # Mapping of STORE_ID to (region_code, store_code) for distributed multi-store setup
    STORE_ID_MAPPING = {
        "store-a": ("A", "A001"),
        "store-b": ("B", "B001"),
        "store-c": ("C", "C001"),
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding.",
        )
        parser.add_argument(
            "--skip-imports",
            action="store_true",
            help="Skip loading the sample CSV imports.",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("SEED_USER_PASSWORD", "FloatStack123!"),
            help="Password applied to seeded users.",
        )

    @property
    def seed_csv_dir(self) -> Path:
        return Path(__file__).resolve().parents[4] / "seed" / "csv"

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo_data()

        password = options["password"]

        # Check if running in distributed mode (STORE_ID set)
        store_id = os.getenv("STORE_ID", "").lower()
        region_code, store_code = None, None
        if store_id in self.STORE_ID_MAPPING:
            region_code, store_code = self.STORE_ID_MAPPING[store_id]
            self.stdout.write(
                f"Seeding data for {store_id} (region={region_code}, store={store_code})"
            )

        regions = self._seed_regions(region_code=region_code)
        stores = self._seed_stores(regions, store_code=store_code)
        hubs = self._seed_hubs(regions)
        inventory_items = self._seed_inventory_catalog()
        users = self._seed_users(password=password, regions=regions, stores=stores)
        self._seed_balances(stores=stores, hubs=hubs, inventory_items=inventory_items)

        # Only seed full demo data in non-distributed mode
        if not region_code:
            self._seed_suppliers(
                stores=stores, regions=regions, inventory_items=inventory_items, users=users
            )
            machine_types = self._seed_machine_types()
            machines = self._seed_machines(stores=stores, machine_types=machine_types)
            self._seed_maintenance_policies(regions=regions, machine_types=machine_types)
            self._seed_orders(stores=stores, users=users)
            self._seed_customer_preferences(users=users)
            self._seed_transfers(
                stores=stores, hubs=hubs, inventory_items=inventory_items, users=users
            )

            if not options["skip_imports"]:
                self._run_sample_imports(users=users)
                self._seed_repair_work(users=users)

            self._seed_notifications(users=users)
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data bootstrapped: "
                f"{Region.objects.count()} regions, "
                f"{Store.objects.count()} stores, "
                f"{SupplyHub.objects.count()} hubs, "
                f"{User.objects.count()} users."
            )
        )

    def _reset_demo_data(self):
        self.stdout.write("Resetting prompt-2 demo data...")
        Notification.objects.all().delete()
        AuditLog.objects.all().delete()
        SyncOutboxEvent.objects.all().delete()
        RevenueLedgerEntry.objects.all().delete()
        PaymentTransaction.objects.all().delete()
        Order.objects.all().delete()
        RepairAssignment.objects.all().delete()
        MachineStatusEvent.objects.all().delete()
        Machine.objects.all().delete()
        MaintenancePolicy.objects.all().delete()
        MachineType.objects.all().delete()
        SupplyTransfer.objects.all().delete()
        HubInventoryBalance.objects.all().delete()
        StoreInventoryBalance.objects.all().delete()
        RestockAlert.objects.all().delete()
        SupplierReplenishment.objects.all().delete()
        LocalSupplier.objects.all().delete()
        SupplySchedule.objects.all().delete()
        SupplyUsageRecord.objects.all().delete()
        ImportJob.objects.all().delete()
        InventoryItem.objects.all().delete()
        SupplyHub.objects.all().delete()
        UserStoreAssignment.objects.all().delete()
        UserRegionAssignment.objects.all().delete()
        User.objects.filter(email__iendswith="@floatstack.local").delete()
        User.objects.filter(email__iendswith="@codepop.local").delete()
        Store.objects.all().delete()
        Region.objects.all().delete()

    def _seed_regions(self, region_code=None):
        regions = {}
        # If region_code specified, only seed that region (distributed mode)
        codes_to_seed = [region_code] if region_code else REGION_DEFINITIONS.keys()

        for code in codes_to_seed:
            if code not in REGION_DEFINITIONS:
                continue
            definition = REGION_DEFINITIONS[code]
            region, _ = Region.objects.update_or_create(
                code=code,
                defaults={
                    "name": definition["name"],
                    "hub_city": definition["hub_city"],
                    "hub_state_code": definition["hub_state_code"],
                    "center_latitude": Decimal(definition["latitude"]),
                    "center_longitude": Decimal(definition["longitude"]),
                    "notes": f"Primary supply region {code}.",
                },
            )
            regions[code] = region
        return regions

    def _seed_stores(self, regions, store_code=None):
        stores = {}
        for region_code, rows in STORE_DEFINITIONS.items():
            # Skip regions not in our loaded regions (distributed mode filter)
            if region_code not in regions:
                continue

            for (
                code,
                name,
                city,
                state_code,
                address,
                postal_code,
                latitude,
                longitude,
            ) in rows:
                # If store_code specified, only seed that store (distributed mode)
                if store_code and code != store_code:
                    continue

                store, _ = Store.objects.update_or_create(
                    store_code=code,
                    defaults={
                        "region": regions[region_code],
                        "slug": slugify(f"{code}-{name}"),
                        "name": name,
                        "city": city,
                        "state_code": state_code,
                        "address_line_1": address,
                        "postal_code": postal_code,
                        "latitude": Decimal(latitude),
                        "longitude": Decimal(longitude),
                        "contact_email": f"{code.lower()}@floatstack.local",
                        "timezone": "America/Denver",
                        "is_active": True,
                    },
                )
                stores[code] = store
        return stores

    def _seed_hubs(self, regions):
        hubs = {}
        for code, region in regions.items():
            hub, _ = SupplyHub.objects.update_or_create(
                hub_code=f"HUB-{code}",
                defaults={
                    "region": region,
                    "name": f"Region {code} Supply Hub",
                    "city": region.hub_city,
                    "state_code": region.hub_state_code,
                    "latitude": region.center_latitude,
                    "longitude": region.center_longitude,
                    "is_active": True,
                    "notes": f"Primary hub for Region {code}.",
                },
            )
            hubs[code] = hub
        return hubs

    def _seed_inventory_catalog(self):
        inventory_items = {}
        for (
            sku,
            name,
            category,
            unit_of_measure,
            threshold,
            is_perishable,
            requires_frozen_storage,
        ) in catalog_inventory_definitions():
            item, _ = InventoryItem.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": category,
                    "unit_of_measure": unit_of_measure,
                    "default_low_stock_threshold": Decimal(threshold),
                    "is_perishable": is_perishable,
                    "requires_frozen_storage": requires_frozen_storage,
                    "is_active": True,
                },
            )
            inventory_items[sku] = item
        return inventory_items

    def _seed_users(self, *, password, regions, stores):
        users = {}

        def upsert_user(
            email,
            *,
            role,
            first_name,
            last_name,
            default_region=None,
            preferred_store=None,
            is_superuser=False,
        ):
            user, _ = User.objects.get_or_create(email=email)
            user.first_name = first_name
            user.last_name = last_name
            user.role = role
            user.status = User.Status.ACTIVE
            user.default_region = default_region
            user.preferred_store = preferred_store
            user.is_email_verified = True
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()
            users[email] = user
            return user

        for region_code, region in regions.items():
            upsert_user(
                f"logistics.{region_code.lower()}@floatstack.local",
                role=User.Role.LOGISTICS_MANAGER,
                first_name=f"Logistics {region_code}",
                last_name="Manager",
                default_region=region,
            )

        super_admin = upsert_user(
            "superadmin@floatstack.local",
            role=User.Role.SUPER_ADMIN,
            first_name="System",
            last_name="Admin",
            default_region=next(iter(regions.values())) if regions else None,
            is_superuser=True,
        )
        users["super_admin"] = super_admin

        for store_code in PRIMARY_STORE_CODES:
            if store_code not in stores:
                continue
            store = stores[store_code]
            manager = upsert_user(
                f"manager.{store_code.lower()}@floatstack.local",
                role=User.Role.MANAGER,
                first_name=store.name.split()[0],
                last_name="Manager",
                default_region=store.region,
                preferred_store=store,
            )
            admin = upsert_user(
                f"admin.{store_code.lower()}@floatstack.local",
                role=User.Role.ADMIN,
                first_name=store.name.split()[0],
                last_name="Admin",
                default_region=store.region,
                preferred_store=store,
            )
            UserStoreAssignment.objects.get_or_create(
                user=manager,
                store=store,
                assignment_type=UserStoreAssignment.AssignmentType.MANAGER_SCOPE,
            )
            UserStoreAssignment.objects.get_or_create(
                user=admin,
                store=store,
                assignment_type=UserStoreAssignment.AssignmentType.ADMIN_SCOPE,
            )

        account_rows = [
            ("account.casey@floatstack.local", "Casey", "Customer", "C001"),
            ("account.river@floatstack.local", "River", "Customer", "C009"),
            ("account.jules@floatstack.local", "Jules", "Customer", "F001"),
        ]
        for email, first_name, last_name, preferred_store_code in account_rows:
            if preferred_store_code not in stores:
                continue
            preferred_store = stores[preferred_store_code]
            upsert_user(
                email,
                role=User.Role.ACCOUNT_USER,
                first_name=first_name,
                last_name=last_name,
                default_region=preferred_store.region,
                preferred_store=preferred_store,
            )

        # In distributed mode (region_code set), also create account users per store
        # for testing cross-store federated login
        if region_code and stores:
            # Get the first (and only) store in this seeding
            store = next(iter(stores.values()))
            account_email = f"account.{store.store_code.lower()}@floatstack.local"
            upsert_user(
                account_email,
                role=User.Role.ACCOUNT_USER,
                first_name=store.name.split()[0],
                last_name="Customer",
                default_region=store.region,
                preferred_store=store,
            )

        repair_people = {
            "repair.north@floatstack.local": ("Cache", "North"),
            "repair.metro@floatstack.local": ("Wasatch", "Metro"),
            "repair.south@floatstack.local": ("Utah", "South"),
        }
        for email, (first_name, last_name) in repair_people.items():
            assigned_stores = REPAIR_ASSIGNMENTS.get(email.split("@")[0], [])
            # Only create repair staff if they have assigned stores in this seeding
            available_stores = [sc for sc in assigned_stores if sc in stores]
            if not available_stores:
                continue

            user = upsert_user(
                email,
                role=User.Role.REPAIR_STAFF,
                first_name=first_name,
                last_name=last_name,
                default_region=stores[available_stores[0]].region,
                preferred_store=stores[available_stores[0]],
            )
            for store_code in available_stores:
                UserStoreAssignment.objects.get_or_create(
                    user=user,
                    store=stores[store_code],
                    assignment_type=UserStoreAssignment.AssignmentType.REPAIR_SCOPE,
                )

        for region_code, region in regions.items():
            logistics_manager = users[
                f"logistics.{region_code.lower()}@floatstack.local"
            ]
            UserRegionAssignment.objects.get_or_create(
                user=logistics_manager,
                region=region,
                assignment_type=UserRegionAssignment.AssignmentType.LOGISTICS_SCOPE,
            )

        return users

    def _seed_balances(self, *, stores, hubs, inventory_items):
        ordered_items = list(inventory_items.values())
        for index, store in enumerate(Store.objects.order_by("store_code"), start=1):
            for item_index, item in enumerate(ordered_items, start=1):
                balance = get_store_balance(store, item)
                threshold = item.default_low_stock_threshold
                if (
                    store.region.code == "C"
                    and index % 5 == 0
                    and item.sku in {"SYRUP-STRAWBERRY", "CUPS-24OZ"}
                ):
                    on_hand = max(threshold - Decimal("1.00"), Decimal("1.00"))
                else:
                    multiplier = Decimal(str(2 + ((index + item_index) % 3)))
                    on_hand = threshold * multiplier
                balance.on_hand_quantity = on_hand
                balance.reserved_quantity = Decimal("0.00")
                balance.reorder_threshold = threshold
                balance.save()
                evaluate_restock_alert(balance)

        for hub_index, hub in enumerate(
            SupplyHub.objects.order_by("hub_code"), start=1
        ):
            for item_index, item in enumerate(ordered_items, start=1):
                balance = get_hub_balance(hub, item)
                balance.on_hand_quantity = item.default_low_stock_threshold * Decimal(
                    str(12 + hub_index + item_index)
                )
                balance.reserved_quantity = Decimal("0.00")
                balance.save()

    def _seed_suppliers(self, *, stores, regions, inventory_items, users):
        supplier_rows = [
            (
                "Cache Valley Dairy",
                "C",
                "Morgan Supplier",
                "cache-dairy@floatstack.local",
                "801-555-0110",
            ),
            (
                "Treasure Valley Beverage",
                "G",
                "Parker Supply",
                "treasure-bev@floatstack.local",
                "208-555-0140",
            ),
            (
                "Sonoran Packaging",
                "F",
                "Avery Vendor",
                "sonoran-pack@floatstack.local",
                "602-555-0190",
            ),
        ]
        suppliers = {}
        for name, region_code, contact_name, email, phone_number in supplier_rows:
            # Only create supplier if region exists in this seeding
            if region_code not in regions:
                continue

            supplier, _ = LocalSupplier.objects.update_or_create(
                name=name,
                defaults={
                    "service_region": regions[region_code],
                    "contact_name": contact_name,
                    "email": email,
                    "phone_number": phone_number,
                    "item_categories_json": [
                        InventoryItem.Category.SODA,
                        InventoryItem.Category.SYRUP,
                        InventoryItem.Category.CUPS,
                    ],
                    "is_active": True,
                },
            )
            suppliers[region_code] = supplier

        replenishment_rows = [
            ("C", "C003", "ICECREAM-VANILLA", "12.00", "repair.north@floatstack.local"),
            ("G", "G002", "BASE-COKE", "30.00", "logistics.g@floatstack.local"),
            ("F", "F003", "CUPS-24OZ", "800.00", "logistics.f@floatstack.local"),
        ]
        for (
            region_code,
            store_code,
            sku,
            quantity_received,
            recorded_by_email,
        ) in replenishment_rows:
            # Skip if supplier, store, user, or sku don't exist in this seeding
            if (region_code not in suppliers or store_code not in stores or
                recorded_by_email not in users or sku not in inventory_items):
                continue

            SupplierReplenishment.objects.update_or_create(
                supplier=suppliers[region_code],
                store=stores[store_code],
                inventory_item=inventory_items[sku],
                defaults={
                    "quantity_requested": Decimal(quantity_received),
                    "quantity_received": Decimal(quantity_received),
                    "requested_by": users[recorded_by_email],
                    "ordered_at": timezone.now() - timedelta(days=3),
                    "expected_delivery_date": timezone.now().date() - timedelta(days=2),
                    "received_at": timezone.now() - timedelta(days=2),
                    "recorded_by": users[recorded_by_email],
                    "unit_cost": Decimal("14.50"),
                    "status": SupplierReplenishment.Status.RECEIVED,
                    "notes": "DEMO historical replenishment receipt",
                },
            )

        pending_order_rows = [
            ("C", "C007", "CUPS-24OZ", "500.00", "logistics.c@floatstack.local"),
            ("G", "G001", "SYRUP-CHERRY", "24.00", "logistics.g@floatstack.local"),
        ]
        for (
            region_code,
            store_code,
            sku,
            quantity_requested,
            requested_by_email,
        ) in pending_order_rows:
            # Skip if supplier, store, user, or sku don't exist in this seeding
            if (region_code not in suppliers or store_code not in stores or
                requested_by_email not in users or sku not in inventory_items):
                continue

            SupplierReplenishment.objects.update_or_create(
                supplier=suppliers[region_code],
                store=stores[store_code],
                inventory_item=inventory_items[sku],
                status=SupplierReplenishment.Status.ORDERED,
                defaults={
                    "quantity_requested": Decimal(quantity_requested),
                    "quantity_received": Decimal("0.00"),
                    "requested_by": users[requested_by_email],
                    "ordered_at": timezone.now() - timedelta(hours=10),
                    "expected_delivery_date": timezone.now().date() + timedelta(days=2),
                    "received_at": None,
                    "recorded_by": users[requested_by_email],
                    "unit_cost": Decimal("18.00"),
                    "notes": "DEMO pending supplier order",
                },
            )

    def _seed_machine_types(self):
        machine_types = {}
        for (
            code,
            name,
            default_interval,
            warning_days,
            error_days,
        ) in MACHINE_TYPE_DEFINITIONS:
            machine_type, _ = MachineType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "default_service_interval_days": default_interval,
                    "warning_max_operational_days": warning_days,
                    "error_max_days": error_days,
                    "is_active": True,
                },
            )
            machine_types[code] = machine_type
        return machine_types

    def _seed_machines(self, *, stores, machine_types):
        machine_specs = [
            ("C001", "MIXER_A", date(2025, 7, 1)),
            ("C002", "CARBONATOR_X", date(2025, 8, 15)),
            ("C003", "FREEZER_SOFTSERVE", date(2025, 9, 1)),
            ("C004", "MIXER_A", date(2025, 6, 20)),
            ("C009", "CARBONATOR_X", date(2025, 5, 10)),
            ("F001", "MIXER_A", date(2025, 6, 1)),
            ("G001", "MIXER_A", date(2025, 6, 5)),
        ]
        machines = {}
        for store_code, machine_type_code, operational_from_date in machine_specs:
            # Skip if store or machine type not in this seeding
            if store_code not in stores or machine_type_code not in machine_types:
                continue

            store = stores[store_code]
            machine_uid = (
                f"{store_code}-{machine_type_code}-{operational_from_date.isoformat()}"
            )
            machine, _ = Machine.objects.update_or_create(
                machine_uid=machine_uid,
                defaults={
                    "store": store,
                    "machine_type": machine_types[machine_type_code],
                    "display_name": f"{store.name} {machine_type_code}",
                    "operational_from_date": operational_from_date,
                    "current_status": Machine.Status.NORMAL,
                    "current_status_date": operational_from_date,
                    "last_service_date": operational_from_date,
                    "next_service_due_date": operational_from_date
                    + timedelta(
                        days=machine_types[
                            machine_type_code
                        ].default_service_interval_days
                    ),
                    "is_active": True,
                },
            )
            if not machine.status_events.exists():
                append_machine_status_event(
                    machine,
                    status=Machine.Status.NORMAL,
                    status_date=operational_from_date,
                )
            machines[machine_uid] = machine
        return machines

    def _seed_maintenance_policies(self, *, regions, machine_types):
        policy_rows = [
            ("MIXER_A", "C", 30, 2, 7),
            ("CARBONATOR_X", "C", 21, 1, 5),
            ("FREEZER_SOFTSERVE", "C", 14, 1, 3),
        ]
        for (
            machine_type_code,
            region_code,
            max_days,
            warning_days,
            schedule_days,
        ) in policy_rows:
            # Skip if region or machine type not in this seeding
            if region_code not in regions or machine_type_code not in machine_types:
                continue

            MaintenancePolicy.objects.update_or_create(
                machine_type=machine_types[machine_type_code],
                region=regions[region_code],
                defaults={
                    "max_days_between_service": max_days,
                    "warning_shutdown_days": warning_days,
                    "schedule_service_window_days": schedule_days,
                    "is_active": True,
                },
            )

    def _seed_orders(self, *, stores, users):
        demo_order_rows = [
            {
                "public_order_code": "FS-Q7N4RX",
                "locker_code": "183",
                "store_code": "C001",
                "customer_email": "account.casey@floatstack.local",
                "guest_contact": None,
                "payment_intent": "pi_demo_account_001",
                "post_payment_transitions": [
                    Order.Status.QUEUED,
                    Order.Status.PREPARING,
                    Order.Status.READY,
                ],
            },
            {
                "public_order_code": "FS-M5K9TD",
                "locker_code": "624",
                "store_code": "C002",
                "customer_email": None,
                "guest_contact": {
                    "display_name": "Taylor Guest",
                    "email": "guest.lookup@floatstack.local",
                    "phone_number": "801-555-0199",
                    "lookup_code": "GST-DEMO-001",
                },
                "payment_intent": "pi_demo_guest_001",
                "post_payment_transitions": [Order.Status.QUEUED],
            },
            {
                "public_order_code": "FS-R8W3PL",
                "locker_code": "907",
                "store_code": "C003",
                "customer_email": "account.river@floatstack.local",
                "guest_contact": None,
                "payment_intent": "pi_demo_refund_001",
                "refund": True,
            },
        ]

        item_payload = [
            build_cart_item(
                drink_slug="berry-burst",
                size="large",
                soda="sprite",
                syrups=["strawberry", "coconut"],
                add_ins=["cream"],
                quantity=1,
                notes="Demo berry build",
            ),
            build_cart_item(
                drink_slug="pepper-cherry-stack",
                size="medium",
                soda="dr-pepper",
                syrups=["cherry", "vanilla"],
                add_ins=[],
                quantity=1,
                notes="Demo cola build",
            ),
        ]

        for row in demo_order_rows:
            if Order.objects.filter(
                public_order_code=row["public_order_code"]
            ).exists():
                continue

            # Skip if store or customer not in this seeding
            if row["store_code"] not in stores:
                continue
            if row["customer_email"] and row["customer_email"] not in users:
                continue

            customer = (
                users.get(row["customer_email"]) if row["customer_email"] else None
            )
            order = create_order(
                store=stores[row["store_code"]],
                items=item_payload,
                customer=customer,
                guest_contact=row["guest_contact"],
                actor=customer,
            )
            order.public_order_code = row["public_order_code"]
            order.locker_code = row.get("locker_code", order.locker_code)
            order.save(update_fields=["public_order_code", "locker_code"])
            record_payment_pending(order, payment_intent_id=row["payment_intent"])
            record_payment_success(
                order, payment_intent_id=row["payment_intent"], actor=customer
            )
            for status in row.get("post_payment_transitions", []):
                if order.status != status:
                    transition_order_status(order, status, actor=customer)
            if row.get("refund"):
                record_refund(
                    order,
                    actor=users["super_admin"],
                    notes="Demo refund before preparation.",
                )

    def _seed_customer_preferences(self, *, users):
        casey = users["account.casey@floatstack.local"]
        river = users["account.river@floatstack.local"]
        jules = users["account.jules@floatstack.local"]

        save_preference_profile(
            user=casey,
            favorite_sodas=["sprite", "root-beer", "cream-soda", "coke"],
            favorite_syrups=["coconut", "lime", "strawberry", "vanilla"],
            favorite_add_ins=["cream", "coconut-cream", "whip"],
            favorite_ice_creams=["scoop-vanilla"],
            disliked_ingredients=["grapefruit"],
            dietary_preferences=[],
            sweetness_preference=User.SweetnessPreference.SWEET,
            adventurousness_preference=User.AdventurousnessPreference.BALANCED,
        )
        save_preference_profile(
            user=river,
            favorite_sodas=["sprite-zero", "diet-coke", "club-soda", "diet-dr-pepper"],
            favorite_syrups=["blackberry", "lime", "lavender"],
            favorite_add_ins=["fresh-mint", "lime-wedge"],
            favorite_ice_creams=[],
            disliked_ingredients=["cream", "half-and-half", "whip"],
            dietary_preferences=["dairy-free", "zero-sugar"],
            sweetness_preference=User.SweetnessPreference.LIGHT,
            adventurousness_preference=User.AdventurousnessPreference.ADVENTUROUS,
        )
        save_preference_profile(
            user=jules,
            favorite_sodas=["mountain-dew", "orange-soda", "sprite", "pepsi"],
            favorite_syrups=["mango", "guava", "passion-fruit", "blue-raspberry"],
            favorite_add_ins=["mango-puree", "strawberry-puree", "fresh-mint"],
            favorite_ice_creams=["scoop-strawberry"],
            disliked_ingredients=["hazelnut"],
            dietary_preferences=[],
            sweetness_preference=User.SweetnessPreference.EXTRA_SWEET,
            adventurousness_preference=User.AdventurousnessPreference.ADVENTUROUS,
        )

        casey_favorite = build_cart_item(
            drink_slug="berry-burst",
            size="large",
            soda="sprite",
            syrups=["strawberry", "coconut"],
            add_ins=["cream"],
            ice_cream="scoop-vanilla",
            quantity=1,
            notes="Casey's creamy weekend float",
        )
        save_favorite_drink(
            user=casey,
            name="Casey's Weekend Float",
            recipe_key="berry-burst",
            size_snapshot=casey_favorite["size"],
            base_price_snapshot=Decimal(casey_favorite["base_price"]),
            customizations_json=casey_favorite["customizations"],
            description=casey_favorite["description"],
        )
        casey_favorite_two = build_cart_item(
            drink_slug="orange-creamsicle",
            size="medium",
            soda="orange-soda",
            syrups=["vanilla"],
            add_ins=["cream"],
            ice_cream="scoop-vanilla",
            quantity=1,
            notes="Dessert-leaning favorite",
        )
        save_favorite_drink(
            user=casey,
            name="Casey's Orange Cream",
            recipe_key="orange-creamsicle",
            size_snapshot=casey_favorite_two["size"],
            base_price_snapshot=Decimal(casey_favorite_two["base_price"]),
            customizations_json=casey_favorite_two["customizations"],
            description=casey_favorite_two["description"],
        )

        river_favorite = build_cart_item(
            drink_slug="citrus-mint-drive",
            size="medium",
            soda="sprite-zero",
            syrups=["lime", "lavender"],
            add_ins=["fresh-mint"],
            ice_cream="",
            quantity=1,
            notes="Keep it crisp",
        )
        save_favorite_drink(
            user=river,
            name="River's Crisp Citrus",
            recipe_key="citrus-mint-drive",
            size_snapshot=river_favorite["size"],
            base_price_snapshot=Decimal(river_favorite["base_price"]),
            customizations_json=river_favorite["customizations"],
            description=river_favorite["description"],
        )
        river_favorite_two = build_cart_item(
            drink_slug="club-citrus-cooler",
            size="medium",
            soda="club-soda",
            syrups=["grapefruit", "lime"],
            add_ins=["fresh-mint"],
            ice_cream="",
            quantity=1,
            notes="Low-sweetness refresher",
        )
        save_favorite_drink(
            user=river,
            name="River's Club Cooler",
            recipe_key="club-citrus-cooler",
            size_snapshot=river_favorite_two["size"],
            base_price_snapshot=Decimal(river_favorite_two["base_price"]),
            customizations_json=river_favorite_two["customizations"],
            description=river_favorite_two["description"],
        )
        jules_favorite = build_cart_item(
            drink_slug="dew-tropic-rush",
            size="large",
            soda="diet-mountain-dew",
            syrups=["mango", "guava"],
            add_ins=[],
            ice_cream="",
            quantity=1,
            notes="Tropical and bright",
        )
        save_favorite_drink(
            user=jules,
            name="Jules' Tropic Dew",
            recipe_key="dew-tropic-rush",
            size_snapshot=jules_favorite["size"],
            base_price_snapshot=Decimal(jules_favorite["base_price"]),
            customizations_json=jules_favorite["customizations"],
            description=jules_favorite["description"],
        )
        jules_favorite_two = build_cart_item(
            drink_slug="mountain-berry-stride",
            size="large",
            soda="mountain-dew",
            syrups=["blue-raspberry", "lime"],
            add_ins=[],
            ice_cream="",
            quantity=1,
            notes="High-energy berry profile",
        )
        save_favorite_drink(
            user=jules,
            name="Jules' Berry Stride",
            recipe_key="mountain-berry-stride",
            size_snapshot=jules_favorite_two["size"],
            base_price_snapshot=Decimal(jules_favorite_two["base_price"]),
            customizations_json=jules_favorite_two["customizations"],
            description=jules_favorite_two["description"],
        )

    def _seed_transfers(self, *, stores, hubs, inventory_items, users):
        same_region_transfer = SupplyTransfer.objects.filter(
            notes="DEMO same-region transfer"
        ).first()
        if same_region_transfer is None:
            same_region_transfer = request_transfer(
                requested_by=users["manager.c001@floatstack.local"],
                source_store=stores["C001"],
                destination_store=stores["C002"],
                line_items=[
                    {
                        "inventory_item": inventory_items["SYRUP-VANILLA"],
                        "quantity_requested": Decimal("3.00"),
                    }
                ],
                notes="DEMO same-region transfer",
                is_ai_draft=True,
            )
            approve_transfer(
                same_region_transfer,
                approver=users["logistics.c@floatstack.local"],
            )

        cross_region_transfer = SupplyTransfer.objects.filter(
            notes="DEMO cross-region hub transfer"
        ).first()
        if cross_region_transfer is None:
            cross_region_transfer = request_transfer(
                requested_by=users["logistics.c@floatstack.local"],
                source_hub=hubs["G"],
                destination_store=stores["C005"],
                line_items=[
                    {
                        "inventory_item": inventory_items["CUPS-24OZ"],
                        "quantity_requested": Decimal("120.00"),
                    }
                ],
                notes="DEMO cross-region hub transfer",
                is_ai_draft=True,
            )
            approve_transfer(
                cross_region_transfer,
                approver=users["logistics.c@floatstack.local"],
            )
            reserve_transfer_inventory(cross_region_transfer)
            ship_transfer(cross_region_transfer)
            deliver_transfer(cross_region_transfer)
            receive_transfer(
                cross_region_transfer, actor=users["manager.c002@floatstack.local"]
            )

    def _run_sample_imports(self, *, users):
        supply_job_exists = ImportJob.objects.filter(
            import_type=ImportJob.ImportType.SUPPLY_USAGE,
            original_filename="supply_usage_sample.csv",
            status=ImportJob.Status.SUCCEEDED,
        ).exists()
        if not supply_job_exists:
            import_supply_usage_csv(
                self.seed_csv_dir.joinpath("supply_usage_sample.csv").read_text(),
                uploaded_by=users["logistics.c@floatstack.local"],
                original_filename="supply_usage_sample.csv",
            )

        repair_job_exists = ImportJob.objects.filter(
            import_type=ImportJob.ImportType.REPAIR_STATUS,
            original_filename="maintenance_schedule_sample.csv",
            status=ImportJob.Status.SUCCEEDED,
        ).exists()
        if not repair_job_exists:
            import_repair_status_csv(
                self.seed_csv_dir.joinpath(
                    "maintenance_schedule_sample.csv"
                ).read_text(),
                uploaded_by=users["repair.north@floatstack.local"],
                original_filename="maintenance_schedule_sample.csv",
            )

        schedule = (
            SupplySchedule.objects.filter(created_by_ai=True)
            .order_by("created_at")
            .first()
        )
        if schedule and schedule.status == SupplySchedule.Status.DRAFT:
            approve_supply_schedule(
                schedule, approver=users["logistics.c@floatstack.local"]
            )

    def _seed_repair_work(self, *, users):
        warning_machine = Machine.objects.filter(
            store__store_code="C001",
            machine_type__code="MIXER_A",
        ).first()
        if warning_machine:
            evaluate_warning_escalation(
                warning_machine,
                as_of_date=date(2026, 3, 18),
                actor=users["repair.north@floatstack.local"],
            )
            if not warning_machine.repair_assignments.exists():
                create_repair_assignment(
                    warning_machine,
                    assigned_to=users["repair.north@floatstack.local"],
                    priority_score=Decimal("90.00"),
                    scheduled_for=timezone.now() + timedelta(hours=2),
                    created_by_system=True,
                    notes="Escalated warning demo assignment.",
                )

        error_machine = Machine.objects.filter(
            store__store_code="C002",
            machine_type__code="CARBONATOR_X",
        ).first()
        if error_machine and not error_machine.repair_assignments.exists():
            create_repair_assignment(
                error_machine,
                assigned_to=users["repair.north@floatstack.local"],
                priority_score=Decimal("75.00"),
                scheduled_for=timezone.now() + timedelta(hours=4),
                created_by_system=True,
                notes="Imported error status demo assignment.",
            )

    def _seed_notifications(self, *, users):
        notification_rows = [
            (
                "manager.c001@floatstack.local",
                "Low stock watch",
                "Logan Main has balances below threshold after queued demo orders.",
            ),
            (
                "logistics.c@floatstack.local",
                "Import review",
                "Supply usage import produced review-ready AI schedule drafts for Region C.",
            ),
            (
                "repair.north@floatstack.local",
                "Repair escalation",
                "A Region C machine escalated from warning to out-of-order.",
            ),
        ]
        for user_email, title, message in notification_rows:
            Notification.objects.get_or_create(
                user=users[user_email],
                title=title,
                defaults={
                    "message": message,
                    "category": Notification.Category.ALERT,
                    "is_read": False,
                },
            )
