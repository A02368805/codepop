"""Federated authentication backend for cross-store login."""

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def _provision_federated_user(data):
    """Create or update a local user record from peer validation response."""
    user, created = User.objects.get_or_create(email=data["email"])
    user.first_name = data.get("first_name", "")
    user.last_name = data.get("last_name", "")
    user.role = data.get("role", User.Role.ACCOUNT_USER)
    user.status = User.Status.ACTIVE
    user.is_email_verified = True

    # Only set unusable password if newly created
    # (if user later registers locally, their password takes precedence)
    if created:
        user.set_unusable_password()

    user.save()
    return user


class FederatedAuthBackend:
    """
    Authenticate against peer stores when user not found locally.

    Inserts after ModelBackend — local users always win. Only fires
    if user doesn't exist locally and PEER_STORES is configured.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        import requests

        # Only run if distributed mode is enabled
        if (
            not settings.PEER_STORES
            or not settings.SYNC_API_SECRET
            or not settings.STORE_ID
        ):
            return None

        # Only try if user doesn't exist locally
        if User.objects.filter(email=username).exists():
            return None  # Let ModelBackend handle it

        # Try each peer store
        for peer_node_id, peer_url in settings.PEER_STORES.items():
            try:
                resp = requests.post(
                    f"{peer_url}/users/federated-validate/",
                    json={"email": username, "password": password},
                    headers={
                        "X-Sync-Token": settings.SYNC_API_SECRET,
                        "X-Origin-Node": settings.STORE_ID,
                    },
                    timeout=5,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("valid"):
                        user_data = data.get("user", {})
                        user = _provision_federated_user(user_data)
                        return user
            except Exception:
                # Peer unreachable or error — try next
                continue

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
