from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .models import Store
from .utils import haversine_miles


def is_home_store(store: Store) -> bool:
    """Return True if this store is the local node's home store."""
    if not settings.HOME_STORE_CODE:
        return True  # non-distributed mode: all stores are local
    return store.store_code == settings.HOME_STORE_CODE


def peer_url_for_store(store: Store) -> str | None:
    """Return the peer URL for a remote store, or None if it's the home store."""
    if is_home_store(store):
        return None
    return settings.PEER_STORE_URLS.get(store.store_code)


@dataclass(frozen=True)
class StoreRecommendation:
    store: Store
    score: Decimal
    distance_miles: Decimal | None
    explanation: str


def recommend_stores(
    *,
    user=None,
    latitude=None,
    longitude=None,
    location_query="",
    pickup_time_requested=None,
    limit=6,
):
    stores = list(Store.objects.filter(is_active=True).select_related("region"))
    recommendations = []
    preferred_store_id = getattr(user, "preferred_store_id", None)
    location_query = location_query.strip().lower()

    now = timezone.now()
    if pickup_time_requested and timezone.is_naive(pickup_time_requested):
        pickup_time_requested = timezone.make_aware(
            pickup_time_requested,
            timezone.get_current_timezone(),
        )

    for store in stores:
        score = Decimal("100.00")
        explanations = []
        distance = None

        if preferred_store_id and store.id == preferred_store_id:
            score += Decimal("18.00")
            explanations.append("Matches your preferred store.")

        if latitude is not None and longitude is not None:
            distance = haversine_miles(
                latitude, longitude, store.latitude, store.longitude
            )
            urgency_penalty = Decimal("0.22")
            if pickup_time_requested and pickup_time_requested <= now + timedelta(
                minutes=45
            ):
                urgency_penalty = Decimal("0.34")
                explanations.append("Closer stores are favored for near-term pickup.")
            score -= distance * urgency_penalty
            explanations.append(
                f"About {distance.quantize(Decimal('0.1'))} miles from your location."
            )
        elif location_query:
            searchable_parts = " ".join(
                [
                    store.name,
                    store.city,
                    store.state_code,
                    store.postal_code,
                    store.address_line_1,
                ]
            ).lower()
            if location_query in searchable_parts:
                score += Decimal("9.00")
                explanations.append("Matches your typed address or ZIP code.")
        elif preferred_store_id is None:
            explanations.append("Active stores are ranked without a location input.")

        if pickup_time_requested and pickup_time_requested >= now + timedelta(hours=2):
            score += Decimal("4.00")
            explanations.append(
                "Future pickup gives more flexibility for store preference."
            )

        recommendations.append(
            StoreRecommendation(
                store=store,
                score=score,
                distance_miles=distance,
                explanation=" ".join(explanations).strip(),
            )
        )

    recommendations.sort(
        key=lambda item: (
            -item.score,
            item.distance_miles or Decimal("9999"),
            item.store.store_code,
        )
    )
    return recommendations[:limit]
