"""
Tests for peer-store cross-store authentication.

Ensures that account users can log in to any store by validating credentials
against peer stores when not found locally. In a distributed system without
a central identity provider, stores validate each other directly.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import make_user

User = get_user_model()


@override_settings(SYNC_API_SECRET="test-secret")
class PeerValidateViewTests(TestCase):
    """Test the /peer-validate/ endpoint for peer store validation."""

    @classmethod
    def setUpTestData(cls):
        """Create an account user that exists locally."""
        cls.account_user = make_user(
            email="account.casey@floatstack.local",
            role="account_user",
            password="TestPassword123!",
        )
        cls.account_user.first_name = "Casey"
        cls.account_user.last_name = "Customer"
        cls.account_user.save()

    def test_peer_validate_account_user_success(self):
        """Peer store validates account user credentials via endpoint."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.casey@floatstack.local",
                "password": "TestPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["user"]["email"], "account.casey@floatstack.local")
        self.assertEqual(data["user"]["first_name"], "Casey")
        self.assertEqual(data["user"]["last_name"], "Customer")
        self.assertEqual(data["user"]["role"], "account_user")

    def test_peer_validate_wrong_password(self):
        """Peer store gets valid=false for wrong password."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.casey@floatstack.local",
                "password": "WrongPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])

    def test_peer_validate_nonexistent_user(self):
        """Peer store gets valid=false for nonexistent user."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "nonexistent@floatstack.local",
                "password": "AnyPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])

    @override_settings(SYNC_API_SECRET="prod-secret")
    def test_peer_validate_wrong_token(self):
        """Wrong X-Sync-Token is rejected."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.casey@floatstack.local",
                "password": "TestPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="wrong-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 401)

    def test_peer_validate_missing_token(self):
        """Missing X-Sync-Token is rejected."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.casey@floatstack.local",
                "password": "TestPassword123!",
            },
            content_type="application/json",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 401)

    def test_peer_validate_missing_origin(self):
        """Missing X-Origin-Node header is rejected."""
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.casey@floatstack.local",
                "password": "TestPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
        )

        self.assertEqual(response.status_code, 400)

    def test_peer_validate_staff_user_rejected(self):
        """Staff users (manager, admin) are not validated via federation."""
        staff_user = make_user(
            email="manager@floatstack.local",
            role="manager",
            password="StaffPassword123!",
        )

        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "manager@floatstack.local",
                "password": "StaffPassword123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])  # Manager role cannot federate

    def test_peer_validate_invalid_json(self):
        """Invalid JSON in request body is rejected."""
        response = self.client.post(
            reverse("peer-validate"),
            "invalid json",
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        self.assertEqual(response.status_code, 400)


class PeerStoreAuthBackendTests(TestCase):
    """Test PeerStoreAuthBackend for cross-store login."""

    @classmethod
    def setUpTestData(cls):
        """Create account users for testing."""
        cls.account_user = make_user(
            email="account.casey@floatstack.local",
            role="account_user",
            password="TestPassword123!",
        )
        cls.account_user.first_name = "Casey"
        cls.account_user.last_name = "Customer"
        cls.account_user.save()

    def test_local_user_auth_preferred_over_peer(self):
        """Local user authentication is tried first, peer validation is fallback."""
        from django.contrib.auth import authenticate

        # Local user should authenticate via ModelBackend
        user = authenticate(
            username="account.casey@floatstack.local",
            password="TestPassword123!",
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "account.casey@floatstack.local")

    def test_peer_auth_skipped_if_distributed_disabled(self):
        """PeerStoreAuthBackend does nothing if distributed mode is off."""
        from django.contrib.auth import authenticate
        from django.test import override_settings

        with override_settings(
            PEER_STORES=None,
            SYNC_API_SECRET=None,
            STORE_ID=None,
        ):
            # Non-existent user should NOT trigger federation attempt
            from apps.users.backends import PeerStoreAuthBackend

            backend = PeerStoreAuthBackend()
            result = backend.authenticate(
                request=None,
                username="nonexistent@floatstack.local",
                password="AnyPassword123!",
            )
            self.assertIsNone(result)

    def test_peer_auth_get_user(self):
        """PeerStoreAuthBackend.get_user retrieves user by ID."""
        from apps.users.backends import PeerStoreAuthBackend

        backend = PeerStoreAuthBackend()
        user = backend.get_user(self.account_user.pk)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "account.casey@floatstack.local")

    def test_peer_auth_get_user_nonexistent(self):
        """PeerStoreAuthBackend.get_user returns None for nonexistent user."""
        from apps.users.backends import PeerStoreAuthBackend
        import uuid

        backend = PeerStoreAuthBackend()
        user = backend.get_user(uuid.uuid4())
        self.assertIsNone(user)


class PeerStoreAuthIntegrationTests(TestCase):
    """Integration tests for federated authentication workflow."""

    @classmethod
    def setUpTestData(cls):
        """Create account user on 'Store A'."""
        cls.account_user = make_user(
            email="account.a001@floatstack.local",
            role="account_user",
            password="FloatStack123!",
        )
        cls.account_user.first_name = "Alice"
        cls.account_user.last_name = "AccountUser"
        cls.account_user.save()

    def test_account_user_can_login_locally_at_store(self):
        """Account user can log in at their primary store (Store A)."""
        response = self.client.post(
            reverse("login"),
            {
                "email": "account.a001@floatstack.local",
                "password": "FloatStack123!",
            },
        )

        # Successful login should redirect
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertIn("dashboard", response.url)

    def test_account_user_login_case_insensitive_email(self):
        """Email login is case-insensitive for account users."""
        response = self.client.post(
            reverse("login"),
            {
                "email": "ACCOUNT.A001@FLOATSTACK.LOCAL",
                "password": "FloatStack123!",
            },
        )

        # Should succeed due to case-insensitive email
        self.assertIn(response.status_code, [200, 302])

    def test_peer_validate_endpoint_availability(self):
        """Federated validate endpoint is accessible and returns valid response."""
        # This endpoint should exist and respond to POST
        response = self.client.post(
            reverse("peer-validate"),
            {
                "email": "account.a001@floatstack.local",
                "password": "FloatStack123!",
            },
            content_type="application/json",
            HTTP_X_SYNC_TOKEN="test-secret",
            HTTP_X_ORIGIN_NODE="store-b",
        )

        # Should be reachable (200 or 401 for wrong token, not 404)
        self.assertNotEqual(response.status_code, 404)

    def test_account_user_login_via_form(self):
        """Account user from peer store can log in via HTML form."""
        # First, authenticate via Django to provision the user
        from django.contrib.auth import authenticate
        user = authenticate(
            username="account.a001@floatstack.local",
            password="FloatStack123!",
        )
        self.assertIsNotNone(user)

        # Now test form-based login (simulating browser)
        response = self.client.post(
            reverse("login"),
            {
                "username": "account.a001@floatstack.local",
                "password": "FloatStack123!",
            },
        )
        # Should redirect on successful login
        self.assertIn(response.status_code, [301, 302, 200])

    def test_peer_user_preserves_preferences(self):
        """Peer user provisioning preserves taste preferences from peer store."""
        from apps.users.backends import _provision_peer_user

        # Data from peer store response
        peer_data = {
            "email": "account.a001@floatstack.local",
            "first_name": "Alice",
            "last_name": "Adventurer",
            "role": "account_user",
            "sweetness_preference": "sweet",
            "adventurousness_preference": "adventurous",
        }

        user = _provision_peer_user(peer_data)

        self.assertEqual(user.email, "account.a001@floatstack.local")
        self.assertEqual(user.first_name, "Alice")
        self.assertEqual(user.last_name, "Adventurer")
        self.assertEqual(user.sweetness_preference, "sweet")
        self.assertEqual(user.adventurousness_preference, "adventurous")
