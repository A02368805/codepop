from datetime import timedelta
from decimal import Decimal

from apps.inventory.services import (
    approve_transfer,
    get_store_balance,
    request_transfer,
)
from apps.orders.services import create_order
from apps.sync.models import SyncConflictLog, SyncOutboxEvent, SyncProjectionState
from apps.sync.services import process_outbox_event
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .helpers import (
    assign_region,
    assign_store,
    make_inventory_item,
    make_region,
    make_store,
    make_user,
)


class SyncWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store_a = make_store(
            store_code="C001",
            region=cls.region,
            name="Logan Main",
        )
        cls.store_b = make_store(
            store_code="C002",
            region=cls.region,
            name="North Logan",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.manager = make_user(
            email="sync-manager@test.local",
            role="manager",
            preferred_store=cls.store_a,
            default_region=cls.region,
        )
        cls.logistics = make_user(
            email="sync-logistics@test.local",
            role="logistics_manager",
            default_region=cls.region,
        )
        assign_store(cls.manager, cls.store_a)
        assign_region(cls.logistics, cls.region)

        cls.inventory_item = make_inventory_item()
        source_balance = get_store_balance(cls.store_a, cls.inventory_item)
        source_balance.on_hand_quantity = Decimal("100.00")
        source_balance.reorder_threshold = Decimal("10.00")
        source_balance.save()

    def _create_transfer(self):
        with self.captureOnCommitCallbacks(execute=True):
            transfer = request_transfer(
                requested_by=self.manager,
                source_store=self.store_a,
                destination_store=self.store_b,
                line_items=[
                    {
                        "inventory_item": self.inventory_item,
                        "quantity_requested": Decimal("5.00"),
                    }
                ],
                notes="Need more syrup for the weekend rush.",
            )
        return transfer

    def test_transfer_events_create_receiver_projections(self):
        from apps.sync.services import process_pending_outbox_events

        transfer = self._create_transfer()
        with self.captureOnCommitCallbacks(execute=True):
            approve_transfer(transfer, approver=self.logistics)

        # Process pending outbox events to create projections
        process_pending_outbox_events(limit=25)

        self.assertTrue(
            SyncProjectionState.objects.filter(
                aggregate_type="SupplyTransfer",
                aggregate_id=str(transfer.pk),
                receiver_scope_type=SyncProjectionState.ReceiverScope.REGION,
                receiver_scope_key=self.region.code,
                last_event_type="transfer.approved",
                last_entity_version=2,
            ).exists()
        )
        self.assertTrue(
            SyncProjectionState.objects.filter(
                aggregate_type="SupplyTransfer",
                aggregate_id=str(transfer.pk),
                receiver_scope_type=SyncProjectionState.ReceiverScope.GLOBAL,
                receiver_scope_key="super_admin",
            ).exists()
        )

    def test_stale_sync_event_is_ignored_and_logged(self):
        from apps.sync.services import process_pending_outbox_events

        transfer = self._create_transfer()
        with self.captureOnCommitCallbacks(execute=True):
            approve_transfer(transfer, approver=self.logistics)

        # Process pending outbox events to create projections
        process_pending_outbox_events(limit=25)

        stale_event = SyncOutboxEvent.objects.create(
            event_type="transfer.requested",
            aggregate_type="SupplyTransfer",
            aggregate_id=str(transfer.pk),
            entity_version=1,
            source_scope={
                "region_code": self.region.code,
                "store_id": str(self.store_b.id),
            },
            payload={"status": "requested"},
        )

        process_outbox_event(stale_event)
        stale_event.refresh_from_db()
        projection = SyncProjectionState.objects.get(
            aggregate_type="SupplyTransfer",
            aggregate_id=str(transfer.pk),
            receiver_scope_type=SyncProjectionState.ReceiverScope.REGION,
            receiver_scope_key=self.region.code,
        )

        self.assertEqual(stale_event.status, SyncOutboxEvent.Status.DISPATCHED)
        self.assertEqual(projection.last_entity_version, 2)
        self.assertTrue(
            SyncConflictLog.objects.filter(
                outbox_event=stale_event,
                conflict_type=SyncConflictLog.ConflictType.STALE_EVENT,
                resolution_status=SyncConflictLog.ResolutionStatus.IGNORED,
            ).exists()
        )

    def test_invalid_scope_event_fails_and_can_be_resolved(self):
        order = create_order(
            store=self.store_a,
            customer=None,
            guest_contact={
                "display_name": "Sync Guest",
                "email": "sync-guest@test.local",
            },
            pickup_time_requested=timezone.now() + timedelta(hours=2),
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.00"),
                    "extras_total": Decimal("0.00"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.00",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=self.manager,
        )
        invalid_event = SyncOutboxEvent.objects.create(
            event_type="order.ready",
            aggregate_type="Order",
            aggregate_id=str(order.pk),
            entity_version=9,
            source_scope={},
            payload={"status": "ready"},
        )

        process_outbox_event(invalid_event)
        invalid_event.refresh_from_db()
        conflict = SyncConflictLog.objects.get(outbox_event=invalid_event)

        self.assertEqual(invalid_event.status, SyncOutboxEvent.Status.FAILED)
        self.assertEqual(
            conflict.conflict_type, SyncConflictLog.ConflictType.INVALID_SCOPE
        )
        self.assertEqual(
            conflict.resolution_status, SyncConflictLog.ResolutionStatus.OPEN
        )

        self.client.force_login(self.logistics)
        response = self.client.post(
            reverse("sync:resolve-conflict", args=[conflict.pk]),
            {
                "resolution_status": SyncConflictLog.ResolutionStatus.RESOLVED,
            },
            HTTP_HX_REQUEST="true",
        )
        conflict.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            conflict.resolution_status, SyncConflictLog.ResolutionStatus.RESOLVED
        )
        self.assertContains(response, "Conflict Log")
