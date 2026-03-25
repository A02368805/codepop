from apps.stores.selectors import regions_visible_to_user, stores_visible_to_user
from apps.supply_hubs.models import SupplyTransfer
from apps.users.permissions import (
    user_can_approve_transfer,
    user_can_manage_machine,
    user_can_progress_transfer,
    user_can_receive_transfer,
    user_can_request_transfer,
    user_has_global_access,
    user_has_region_scope,
    user_has_store_scope,
)
from apps.inventory.services import request_transfer
from django.test import TestCase

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_machine,
    make_machine_type,
    make_region,
    make_store,
    make_user,
)


class RBACScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region_c = make_region(code="C", name="Logan, UT")
        cls.region_g = make_region(
            code="G",
            name="Boise, ID",
            hub_city="Boise",
            hub_state_code="ID",
            latitude="43.615021",
            longitude="-116.202316",
        )
        cls.store_c1 = make_store(
            store_code="C001", region=cls.region_c, name="Logan Main"
        )
        cls.store_c2 = make_store(
            store_code="C002",
            region=cls.region_c,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.store_g1 = make_store(
            store_code="G001",
            region=cls.region_g,
            name="Boise Capitol",
            city="Boise",
            state_code="ID",
            address_line_1="50 Idaho St",
            postal_code="83702",
            latitude="43.615018",
            longitude="-116.202313",
        )

        cls.account_user = make_user(
            email="account@test.local",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.manager = make_user(
            email="manager@test.local",
            role="manager",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.admin = make_user(
            email="admin@test.local",
            role="admin",
            preferred_store=cls.store_c2,
            default_region=cls.region_c,
        )
        cls.logistics = make_user(
            email="logistics@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.repair = make_user(
            email="repair@test.local",
            role="repair_staff",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.super_admin = make_user(
            email="super@test.local",
            role="super_admin",
            default_region=cls.region_c,
            is_superuser=True,
        )

        assign_store(cls.manager, cls.store_c1)
        assign_store(cls.admin, cls.store_c2)
        assign_store(cls.repair, cls.store_c1)
        assign_region(cls.logistics, cls.region_c)

        cls.machine_type = make_machine_type()
        cls.machine = make_machine(store=cls.store_c1, machine_type=cls.machine_type)
        cls.inventory_item = make_inventory_item(sku="SYRUP-RBAC")

        cls.transfer_same_region = request_transfer(
            requested_by=cls.logistics,
            source_store=cls.store_c1,
            destination_store=cls.store_c2,
            line_items=[
                {
                    "inventory_item": cls.inventory_item,
                    "quantity_requested": "1.00",
                }
            ],
            notes="rbac same region",
        )
        cls.transfer_other_region = request_transfer(
            requested_by=cls.super_admin,
            source_store=cls.store_g1,
            destination_store=cls.store_g1,
            line_items=[
                {
                    "inventory_item": cls.inventory_item,
                    "quantity_requested": "1.00",
                }
            ],
            notes="rbac other region",
        )

    def test_store_scope_only_matches_explicit_assignments(self):
        self.assertTrue(user_has_store_scope(self.manager, self.store_c1))
        self.assertFalse(user_has_store_scope(self.manager, self.store_c2))
        self.assertFalse(user_has_store_scope(self.logistics, self.store_c1))

    def test_region_scope_is_reserved_for_region_assignments_or_global_access(self):
        self.assertTrue(user_has_region_scope(self.logistics, self.region_c))
        self.assertFalse(user_has_region_scope(self.logistics, self.region_g))
        self.assertFalse(user_has_region_scope(self.manager, self.region_c))
        self.assertFalse(user_has_region_scope(self.repair, self.region_c))
        self.assertTrue(user_has_region_scope(self.super_admin, self.region_g))

    def test_visibility_selectors_do_not_escape_user_scope(self):
        self.assertQuerySetEqual(
            stores_visible_to_user(self.account_user).order_by("store_code"),
            [self.store_c1],
            transform=lambda store: store,
        )
        self.assertQuerySetEqual(
            stores_visible_to_user(self.manager).order_by("store_code"),
            [self.store_c1],
            transform=lambda store: store,
        )
        self.assertQuerySetEqual(
            stores_visible_to_user(self.logistics).order_by("store_code"),
            [self.store_c1, self.store_c2],
            transform=lambda store: store,
        )
        self.assertQuerySetEqual(
            regions_visible_to_user(self.account_user),
            [self.region_c],
            transform=lambda region: region,
        )

    def test_machine_management_respects_role_scope(self):
        self.assertTrue(user_can_manage_machine(self.manager, self.machine))
        self.assertTrue(user_can_manage_machine(self.repair, self.machine))
        self.assertFalse(user_can_manage_machine(self.admin, self.machine))
        self.assertTrue(user_can_manage_machine(self.super_admin, self.machine))
        self.assertTrue(user_has_global_access(self.super_admin))

    def test_transfer_request_permissions_respect_destination_scope(self):
        self.assertTrue(user_can_request_transfer(self.logistics, self.store_c2))
        self.assertTrue(user_can_request_transfer(self.manager, self.store_c1))
        self.assertFalse(user_can_request_transfer(self.manager, self.store_c2))
        self.assertFalse(user_can_request_transfer(self.repair, self.store_c1))

    def test_transfer_approval_requires_logistics_region_scope_or_global(self):
        self.assertTrue(
            user_can_approve_transfer(self.logistics, self.transfer_same_region)
        )
        self.assertFalse(
            user_can_approve_transfer(self.logistics, self.transfer_other_region)
        )
        self.assertFalse(user_can_approve_transfer(self.manager, self.transfer_same_region))
        self.assertTrue(
            user_can_approve_transfer(self.super_admin, self.transfer_other_region)
        )

    def test_transfer_progress_and_receive_permissions_follow_scope_rules(self):
        self.assertTrue(
            user_can_progress_transfer(self.logistics, self.transfer_same_region)
        )
        self.assertTrue(
            user_can_progress_transfer(self.manager, self.transfer_same_region)
        )
        self.assertFalse(
            user_can_progress_transfer(self.repair, self.transfer_same_region)
        )

        self.assertTrue(user_can_receive_transfer(self.manager, self.transfer_same_region))
        self.assertFalse(
            user_can_receive_transfer(self.repair, self.transfer_same_region)
        )
