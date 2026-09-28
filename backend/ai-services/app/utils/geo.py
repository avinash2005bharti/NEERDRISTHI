import math
from typing import Tuple, List, Optional


EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate the great circle distance between two points on the earth in km.
    Input coordinates: (longitude, latitude)
    """
    lon1, lat1 = coord1
    lon2, lat2 = coord2

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def bounding_box_for_radius(
    lon: float, lat: float, radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate approximate bounding box (min_lon, min_lat, max_lon, max_lat)
    for a given center and radius in kilometers.
    """
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    return (
        max(-180.0, lon - abs(lon_delta)),
        max(-90.0, lat - lat_delta),
        min(180.0, lon + abs(lon_delta)),
        min(90.0, lat + lat_delta),
    )


def is_indian_ocean_region(lon: float, lat: float) -> bool:
    """
    Check if coordinates fall within the broader Indian Ocean & Arabian Sea / Bay of Bengal marine zone.
    Longitude: [50.0, 105.0], Latitude: [-10.0, 30.0]
    """
    return (50.0 <= lon <= 105.0) and (-10.0 <= lat <= 30.0)
