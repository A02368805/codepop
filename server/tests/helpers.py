from datetime import date
from decimal import Decimal

from apps.inventory.models import InventoryItem
from apps.maintenance.models import Machine, MachineType
from apps.stores.models import Region, Store
from apps.supply_hubs.models import SupplyHub
from apps.users.models import User, UserRegionAssignment, UserStoreAssignment
from django.utils.text import slugify


def make_region(
    *,
    code="C",
    name=None,
    hub_city="Logan",
    hub_state_code="UT",
    latitude="41.736980",
    longitude="-111.833836",
):
    return Region.objects.create(
        code=code,
        name=name or f"Region {code}",
        hub_city=hub_city,
        hub_state_code=hub_state_code,
        center_latitude=Decimal(latitude),
        center_longitude=Decimal(longitude),
    )


def make_store(
    *,
    store_code="C001",
    region=None,
    name="Test Store",
    city="Logan",
    state_code="UT",
    address_line_1="123 Main St",
    postal_code="84321",
    latitude="41.736980",
    longitude="-111.833836",
):
    region = region or make_region()
    return Store.objects.create(
        region=region,
        slug=slugify(f"{store_code}-{name}"),
        store_code=store_code,
        name=name,
        city=city,
        state_code=state_code,
        address_line_1=address_line_1,
        postal_code=postal_code,
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        timezone="America/Denver",
    )


def make_user(
    *,
    email,
    role=User.Role.ACCOUNT_USER,
    default_region=None,
    preferred_store=None,
    password="FloatStack123!",
    is_superuser=False,
):
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        default_region=default_region,
        preferred_store=preferred_store,
        is_superuser=is_superuser,
        is_email_verified=True,
    )
    return user


def assign_store(user, store, assignment_type=None):
    assignment_type = assignment_type or {
        User.Role.MANAGER: UserStoreAssignment.AssignmentType.MANAGER_SCOPE,
        User.Role.ADMIN: UserStoreAssignment.AssignmentType.ADMIN_SCOPE,
        User.Role.REPAIR_STAFF: UserStoreAssignment.AssignmentType.REPAIR_SCOPE,
    }.get(user.role, UserStoreAssignment.AssignmentType.PRIMARY)
    return UserStoreAssignment.objects.create(
        user=user,
        store=store,
        assignment_type=assignment_type,
    )


def assign_region(user, region, assignment_type=None):
    assignment_type = (
        assignment_type or UserRegionAssignment.AssignmentType.LOGISTICS_SCOPE
    )
    return UserRegionAssignment.objects.create(
        user=user,
        region=region,
        assignment_type=assignment_type,
    )


def make_inventory_item(
    *,
    sku="SYRUP-STRAWBERRY",
    name="Strawberry Syrup",
    category=InventoryItem.Category.SYRUP,
    threshold="10.00",
):
    return InventoryItem.objects.create(
        sku=sku,
        name=name,
        category=category,
        unit_of_measure="unit",
        default_low_stock_threshold=Decimal(threshold),
    )


def make_hub(
    *,
    hub_code="HUB-C",
    region=None,
    name="Region C Supply Hub",
    city="Logan",
    state_code="UT",
    latitude="41.736980",
    longitude="-111.833836",
):
    region = region or make_region()
    return SupplyHub.objects.create(
        hub_code=hub_code,
        region=region,
        name=name,
        city=city,
        state_code=state_code,
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
    )


def make_machine_type(
    *,
    code="MIXER_A",
    name="Primary Mixer",
    default_service_interval_days=30,
    warning_max_operational_days=2,
    error_max_days=1,
):
    return MachineType.objects.create(
        code=code,
        name=name,
        default_service_interval_days=default_service_interval_days,
        warning_max_operational_days=warning_max_operational_days,
        error_max_days=error_max_days,
    )


def make_machine(
    *,
    store,
    machine_type,
    machine_uid=None,
    display_name=None,
    operational_from_date=None,
):
    operational_from_date = operational_from_date or date(2025, 1, 1)
    machine_uid = (
        machine_uid
        or f"{store.store_code}-{machine_type.code}-{operational_from_date.isoformat()}"
    )
    return Machine.objects.create(
        machine_uid=machine_uid,
        store=store,
        machine_type=machine_type,
        display_name=display_name or machine_uid,
        operational_from_date=operational_from_date,
        current_status=Machine.Status.NORMAL,
        current_status_date=operational_from_date,
        last_service_date=operational_from_date,
        next_service_due_date=operational_from_date,
    )
