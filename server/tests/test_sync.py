import json
from datetime import timedelta
from decimal import Decimal

from apps.inventory.services import (
    approve_transfer,
    get_store_balance,
    request_transfer,
)
from apps.orders.services import create_order
from apps.sync.models import SyncConflictLog, SyncOutboxEvent, SyncProjectionState
from apps.sync.services import process_outbox_event, process_pending_outbox_events
from django.test import TestCase, override_settings
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
        self.assertIsNotNone(conflict.resolved_at)

    def test_sync_panel_shows_projection_and_conflict_sections(self):
        transfer = self._create_transfer()
        with self.captureOnCommitCallbacks(execute=True):
            approve_transfer(transfer, approver=self.logistics)

        stale_event = SyncOutboxEvent.objects.create(
            event_type="transfer.requested",
            aggregate_type="SupplyTransfer",
            aggregate_id=str(transfer.pk),
            entity_version=0,
            source_scope={"region_code": self.region.code},
            payload={"status": "requested"},
        )
        process_outbox_event(stale_event)

        self.client.force_login(self.logistics)
        response = self.client.get(reverse("sync:panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conflict Log")
        self.assertContains(response, "Receiver Projections")


class SyncPeerTransportTests(TestCase):
    """Tests for inter-store peer sync transport layer."""

    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store_a = make_store(
            store_code="C001",
            region=cls.region,
            name="Store A",
        )
        cls.store_b = make_store(
            store_code="C002",
            region=cls.region,
            name="Store B",
            city="North Logan",
            address_line_1="456 Canyon Rd",
            latitude="41.769089",
            longitude="-111.804093",
        )
        cls.manager = make_user(
            email="peer-manager@test.local",
            role="manager",
            preferred_store=cls.store_a,
            default_region=cls.region,
        )
        assign_store(cls.manager, cls.store_a)

    def test_ingest_endpoint_rejects_invalid_token(self):
        """Ingest endpoint returns 401 if X-Sync-Token is missing or invalid."""
        response = self.client.post(
            reverse("sync:ingest"),
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            reverse("sync:ingest"),
            data=b"{}",
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="wrong-secret",
        )
        self.assertEqual(response.status_code, 401)

    def test_ingest_endpoint_rejects_missing_origin(self):
        """Ingest endpoint returns 400 if X-Origin-Node header is missing."""
        from django.test import override_settings

        with override_settings(SYNC_API_SECRET="test-secret"):
            response = self.client.post(
                reverse("sync:ingest"),
                data=b"{}",
                content_type="application/json",
                HTTP_X_SYNC_TOKEN="test-secret",
            )
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertEqual(data["error"], "missing origin")

    def test_ingest_endpoint_accepts_valid_event(self):
        """Ingest endpoint accepts valid event with correct auth and creates SyncOutboxEvent."""
        import uuid

        from django.test import override_settings

        remote_event_id = uuid.uuid4()
        payload = {
            "event_id": str(remote_event_id),
            "event_type": "order.created",
            "aggregate_type": "Order",
            "aggregate_id": str(uuid.uuid4()),
            "entity_version": 1,
            "source_scope": {"store_id": str(self.store_b.id), "region_code": "C"},
            "payload": {"status": "created"},
        }

        with override_settings(SYNC_API_SECRET="test-secret"):
            response = self.client.post(
                reverse("sync:ingest"),
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_SYNC_TOKEN="test-secret",
                HTTP_X_ORIGIN_NODE="store-b",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

        # Verify event was created
        event = SyncOutboxEvent.objects.get(remote_event_id=remote_event_id)
        self.assertEqual(event.origin_node_id, "store-b")
        self.assertEqual(event.event_type, "order.created")

    def test_ingest_deduplicates_repeated_events(self):
        """Repeated ingest of same event (same origin + remote_event_id) is idempotent."""
        import uuid

        from django.test import override_settings

        remote_event_id = uuid.uuid4()
        payload = {
            "event_id": str(remote_event_id),
            "event_type": "order.created",
            "aggregate_type": "Order",
            "aggregate_id": str(uuid.uuid4()),
            "entity_version": 1,
            "source_scope": {"store_id": str(self.store_b.id), "region_code": "C"},
            "payload": {"status": "created"},
        }

        with override_settings(SYNC_API_SECRET="test-secret"):
            response1 = self.client.post(
                reverse("sync:ingest"),
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_SYNC_TOKEN="test-secret",
                HTTP_X_ORIGIN_NODE="store-b",
            )
            response2 = self.client.post(
                reverse("sync:ingest"),
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_SYNC_TOKEN="test-secret",
                HTTP_X_ORIGIN_NODE="store-b",
            )

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Should only have one event
        event_count = SyncOutboxEvent.objects.filter(
            origin_node_id="store-b",
            remote_event_id=remote_event_id,
        ).count()
        self.assertEqual(event_count, 1)

    @override_settings(
        SYNC_PUSH_ENABLED=True,
        STORE_ID="store-a",
        PEER_STORES={"store-b": "http://store-b:8000"},
        SYNC_API_SECRET="test-secret",
    )
    def test_process_outbox_creates_peer_deliveries(self):
        """Processing local outbox event creates SyncPeerDelivery records."""
        from unittest.mock import MagicMock, patch

        from apps.sync.models import SyncPeerDelivery

        # Create a simple outbox event directly
        event = SyncOutboxEvent.objects.create(
            event_type="test.event",
            aggregate_type="Test",
            aggregate_id="test-123",
            entity_version=1,
            source_scope={"store_id": str(self.store_a.id), "region_code": "C"},
            payload={"test": "data"},
        )

        # Mock requests module
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            # Process the event
            process_outbox_event(event)

            # Check that peer deliveries were created
            deliveries = SyncPeerDelivery.objects.filter(
                event=event, peer_node_id="store-b"
            )
            self.assertEqual(
                deliveries.count(), 1, "Peer delivery record was not created"
            )

    def test_ingested_event_does_not_re_push(self):
        """Events received from peers (origin_node_id != '') are not re-pushed."""
        import uuid

        from django.test import override_settings

        # Create an event with a peer origin
        remote_event_id = uuid.uuid4()
        event = SyncOutboxEvent.objects.create(
            event_type="order.created",
            aggregate_type="Order",
            aggregate_id=str(uuid.uuid4()),
            entity_version=1,
            source_scope={"store_id": str(self.store_b.id), "region_code": "C"},
            payload={"status": "created"},
            origin_node_id="store-b",
            remote_event_id=remote_event_id,
        )

        with override_settings(
            SYNC_PUSH_ENABLED=True,
            STORE_ID="store-a",
            PEER_STORES={"store-c": "http://store-c:8000"},
        ):
            from apps.sync.models import SyncPeerDelivery

            # Process the event
            process_outbox_event(event)

            # Should NOT have created peer deliveries (event is from peer, no re-push)
            deliveries = SyncPeerDelivery.objects.filter(event=event)
            self.assertEqual(deliveries.count(), 0)


class NodeHealthViewTests(TestCase):
    """Tests for the /sync/health/ endpoint."""

    def test_health_returns_ok_without_auth(self):
        """Health endpoint returns basic status without auth."""
        response = self.client.get(reverse("sync:health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertNotIn("peers", data)

    @override_settings(STORE_ID="store-a", SYNC_PUSH_ENABLED=True)
    def test_health_returns_node_identity(self):
        """Health endpoint returns configured node ID."""
        response = self.client.get(reverse("sync:health"))
        data = response.json()
        self.assertEqual(data["node_id"], "store-a")
        self.assertTrue(data["sync_enabled"])

    @override_settings(
        STORE_ID="store-a",
        SYNC_API_SECRET="test-secret",
        PEER_STORES={"store-b": "http://unreachable:9999"},
    )
    def test_health_shows_peers_when_authenticated(self):
        """Authenticated request includes peer connectivity info."""
        response = self.client.get(
            reverse("sync:health"),
            HTTP_X_SYNC_TOKEN="test-secret",
        )
        data = response.json()
        self.assertIn("peers", data)
        self.assertIn("store-b", data["peers"])
        self.assertFalse(data["peers"]["store-b"]["reachable"])

    @override_settings(
        STORE_ID="store-a",
        SYNC_API_SECRET="test-secret",
        PEER_STORES={"store-b": "http://store-b:8000"},
    )
    def test_health_probe_header_skips_nested_peer_calls(self):
        """Probe requests should not recurse into peer health checks."""
        from unittest.mock import patch

        with patch("requests.get") as mock_get:
            response = self.client.get(
                reverse("sync:health"),
                HTTP_X_SYNC_TOKEN="test-secret",
                HTTP_X_DISTRIBUTED_HEALTH_PROBE="1",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("peers", data)
        mock_get.assert_not_called()
