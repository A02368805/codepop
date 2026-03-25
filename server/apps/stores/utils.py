from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1, lon1, lat2, lon2) -> Decimal:
    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return Decimal(str(round(EARTH_RADIUS_MILES * c, 2)))
