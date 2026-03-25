from __future__ import annotations

import json
from decimal import Decimal
from urllib.parse import quote_plus
from urllib.request import urlopen

from django.conf import settings


def google_maps_url(address):
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"


def apple_maps_url(address):
    return f"https://maps.apple.com/?q={quote_plus(address)}"


def mapbox_static_map_url(*, latitude, longitude, width=960, height=540):
    token = getattr(settings, "MAPBOX_PUBLIC_TOKEN", "")
    if not token:
        return ""
    return (
        "https://api.mapbox.com/styles/v1/mapbox/light-v11/static/"
        f"pin-s+7A5980({longitude},{latitude})/{longitude},{latitude},13/{width}x{height}"
        f"?access_token={token}"
    )


def geocode_location_query(query):
    token = getattr(settings, "MAPBOX_PUBLIC_TOKEN", "")
    if not token or not query:
        return None
    encoded_query = quote_plus(query.strip())
    url = (
        "https://api.mapbox.com/geocoding/v5/mapbox.places/"
        f"{encoded_query}.json?limit=1&country=US&access_token={token}"
    )
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    features = payload.get("features") or []
    if not features:
        return None
    center = features[0].get("center") or []
    if len(center) != 2:
        return None
    longitude, latitude = center
    return {
        "latitude": Decimal(str(latitude)),
        "longitude": Decimal(str(longitude)),
        "label": features[0].get("place_name", query.strip()),
    }
