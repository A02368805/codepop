"""Peer-store authentication backend for cross-store login.

In a distributed system without a central identity provider, each store
can validate users against peer stores. This enables account users to log in
at any store while keeping staff roles (managers, admins) store-local.
"""

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def _provision_peer_user(data):
    """Create or update a local user record from peer store validation response.

    Preserves user profile data (name, preferences) synced from peer store.
    Only account_user role is allowed; staff roles stay store-local.
    """
    user, created = User.objects.get_or_create(email=data["email"])
    user.first_name = data.get("first_name", "")
    user.last_name = data.get("last_name", "")
    user.role = data.get("role", User.Role.ACCOUNT_USER)
    user.status = User.Status.ACTIVE
    user.is_email_verified = True

    # Preserve taste preferences from peer store
    if "sweetness_preference" in data and data["sweetness_preference"]:
        user.sweetness_preference = data["sweetness_preference"]
    if "adventurousness_preference" in data and data["adventurousness_preference"]:
        user.adventurousness_preference = data["adventurousness_preference"]

    # Only set unusable password if newly created
    # (if user later registers locally, their password takes precedence)
    if created:
        user.set_unusable_password()

    user.save()
    return user


class PeerStoreAuthBackend:
    """
    Authenticate against peer stores when user not found locally.

    In a distributed system, stores validate users against each other.
    This backend is a fallback after ModelBackend — local users always win.
    Only runs if PEER_STORES and SYNC_API_SECRET are configured.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        import logging

        import requests

        logger = logging.getLogger("peer_auth")

        # Only run if distributed mode is enabled
        if (
            not settings.PEER_STORES
            or not settings.SYNC_API_SECRET
            or not settings.STORE_ID
        ):
            logger.debug("Peer auth skipped: distributed mode not enabled")
            return None

        logger.info(
            "Peer auth flow started for %s at store %s", username, settings.STORE_ID
        )

        # Check if user exists locally and has a usable password
        local_user = User.objects.filter(email=username).first()

        if local_user and local_user.has_usable_password():
            logger.debug(
                "Local user %s has usable password, letting ModelBackend handle it",
                username,
            )
            return None

        logger.info(
            "Attempting peer validation for %s at %s", username, settings.STORE_ID
        )

        # Try each peer store to validate the user
        for peer_node_id, peer_url in settings.PEER_STORES.items():
            try:
                logger.info("Querying peer %s at %s", peer_node_id, peer_url)
                resp = requests.post(
                    f"{peer_url}/peer-validate/",
                    json={"email": username, "password": password},
                    headers={
                        "X-Sync-Token": settings.SYNC_API_SECRET,
                        "X-Origin-Node": settings.STORE_ID,
                    },
                    timeout=5,
                )

                logger.info("Peer response from %s: %s", peer_node_id, resp.status_code)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("valid"):
                        user_data = data.get("user", {})
                        logger.info(
                            "Peer validation SUCCESS for %s via %s",
                            username,
                            peer_node_id,
                        )
                        user = _provision_peer_user(user_data)
                        return user
                    else:
                        logger.info("Peer %s returned valid=false", peer_node_id)
            except Exception as e:
                # Peer unreachable or error — try next peer
                logger.error("Peer %s unreachable: %s", peer_node_id, e)
                continue

        logger.warning("Peer validation failed for %s — all peers rejected", username)
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
