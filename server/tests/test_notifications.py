from datetime import date
from decimal import Decimal

from apps.inventory.services import (
    approve_transfer,
    get_store_balance,
    request_transfer,
)
from apps.maintenance.models import Machine
from apps.maintenance.services import append_machine_status_event
from apps.notifications.models import DeviceRegistration, Notification
from django.test import TestCase
from django.urls import reverse

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


class NotificationScopingTests(TestCase):
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
            store_code="C001",
            region=cls.region_c,
            name="Logan Main",
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
        cls.machine_type = make_machine_type(code="MIXER_A")
        cls.machine = make_machine(store=cls.store_c1, machine_type=cls.machine_type)

        cls.manager_c1 = make_user(
            email="manager-c1@test.local",
            role="manager",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.manager_c2 = make_user(
            email="manager-c2@test.local",
            role="manager",
            preferred_store=cls.store_c2,
            default_region=cls.region_c,
        )
        cls.repair_c = make_user(
            email="repair-c@test.local",
            role="repair_staff",
            preferred_store=cls.store_c1,
            default_region=cls.region_c,
        )
        cls.logistics_c = make_user(
            email="logistics-c@test.local",
            role="logistics_manager",
            default_region=cls.region_c,
        )
        cls.logistics_g = make_user(
            email="logistics-g@test.local",
            role="logistics_manager",
            default_region=cls.region_g,
        )

        assign_store(cls.manager_c1, cls.store_c1)
        assign_store(cls.manager_c2, cls.store_c2)
        assign_store(cls.repair_c, cls.store_c1)
        assign_region(cls.logistics_c, cls.region_c)
        assign_region(cls.logistics_g, cls.region_g)

        cls.inventory_item = make_inventory_item(
            sku="SYRUP-STRAWBERRY",
            name="Strawberry Syrup",
        )
        balance = get_store_balance(cls.store_c1, cls.inventory_item)
        balance.on_hand_quantity = Decimal("20.00")
        balance.reorder_threshold = Decimal("5.00")
        balance.save()

    def test_machine_alerts_only_reach_scoped_store_roles(self):
        with self.captureOnCommitCallbacks(execute=True):
            append_machine_status_event(
                self.machine,
                status=Machine.Status.ERROR,
                status_date=date(2026, 3, 25),
                actor=self.repair_c,
            )

        self.assertTrue(
            Notification.objects.filter(
                user=self.manager_c1,
                notification_type=Notification.NotificationType.MACHINE_ALERT,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.repair_c,
                notification_type=Notification.NotificationType.MACHINE_ALERT,
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.manager_c2,
                notification_type=Notification.NotificationType.MACHINE_ALERT,
            ).exists()
        )

    def test_transfer_updates_respect_store_and_region_scope(self):
        transfer = request_transfer(
            requested_by=self.logistics_c,
            source_store=self.store_c1,
            destination_store=self.store_c2,
            line_items=[
                {
                    "inventory_item": self.inventory_item,
                    "quantity_requested": Decimal("2.00"),
                }
            ],
            notes="Need more syrup",
            is_ai_draft=True,
        )

        with self.captureOnCommitCallbacks(execute=True):
            approve_transfer(transfer, approver=self.logistics_c)

        self.assertTrue(
            Notification.objects.filter(
                user=self.manager_c1,
                notification_type=Notification.NotificationType.TRANSFER_UPDATE,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.logistics_c,
                notification_type=Notification.NotificationType.TRANSFER_UPDATE,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager_c2,
                notification_type=Notification.NotificationType.TRANSFER_UPDATE,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.logistics_c,
                notification_type=Notification.NotificationType.TRANSFER_UPDATE,
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.logistics_g,
                notification_type=Notification.NotificationType.TRANSFER_UPDATE,
            ).exists()
        )

    def test_notification_workspace_filters_and_device_registration_work(self):
        notification = Notification.objects.create(
            user=self.manager_c1,
            title="Unread alert",
            message="Needs attention",
            notification_type=Notification.NotificationType.GENERIC,
            delivery_status=Notification.DeliveryStatus.SENT,
        )
        Notification.objects.create(
            user=self.manager_c1,
            title="Read alert",
            message="Already handled",
            notification_type=Notification.NotificationType.GENERIC,
            delivery_status=Notification.DeliveryStatus.SENT,
            is_read=True,
        )

        self.client.force_login(self.manager_c1)
        response = self.client.get(reverse("notifications:index"), {"state": "unread"})
        self.assertContains(response, "Unread alert")
        self.assertNotContains(response, "Read alert")

        response = self.client.post(
            reverse("notifications:mark-all-read"),
            {"state": "unread"},
            HTTP_HX_REQUEST="true",
        )
        notification.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(notification.is_read)

        device_response = self.client.post(
            reverse("notifications:register-device"),
            {
                "device_token": "browser-token-1",
                "platform": DeviceRegistration.Platform.WEB,
                "push_provider": DeviceRegistration.PushProvider.WEB_PUSH,
                "device_label": "Browser",
            },
        )
        self.assertEqual(device_response.status_code, 200)
        self.assertTrue(
            DeviceRegistration.objects.filter(
                user=self.manager_c1,
                device_token="browser-token-1",
            ).exists()
        )
