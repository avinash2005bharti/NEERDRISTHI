"""
GeoPandas/Shapely spatial processing service for ORCA.
Provides deterministic GIS operations:
  - Haversine/geodesic distance
  - Point-in-polygon (restricted zones, protected areas)
  - Buffer queries (50 km around user location)
  - Route intersection with hazard zones
  - Nearest feature finding

All calculations are deterministic. The LLM is NEVER used for spatial reasoning.
"""
from typing import List, Dict, Any, Optional, Tuple
import math
from datetime import datetime, timezone
from ..observability.logger import logger

try:
    from shapely.geometry import Point, Polygon, LineString, shape
    from shapely.ops import unary_union
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    logger.warning("GeoPandas/Shapely not installed. Falling back to haversine-only GIS operations.")


# Earth radius constants
EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_M = 6_378_100.0

# India's approximate maritime EEZ boundary (simplified polygon)
INDIA_EEZ_APPROX = [
    (60.0, 8.0), (77.0, 7.0), (80.5, 9.0), (80.5, 14.0),
    (82.0, 16.0), (80.0, 20.0), (78.0, 24.0), (75.0, 24.0),
    (70.0, 23.0), (68.0, 20.0), (65.0, 16.0), (64.0, 12.0),
    (65.0, 8.0), (60.0, 8.0),
]


class GISService:
    """
    Geospatial processing service using GeoPandas/Shapely.
    Degrades gracefully to haversine math when GeoPandas is unavailable.
    """

    def __init__(self):
        self.available = GEOPANDAS_AVAILABLE
        if not self.available:
            logger.warning("GISService: running in haversine-only fallback mode (install geopandas + shapely for full GIS)")

    # ─── Distance ────────────────────────────────────────────────────────────

    def haversine_distance_km(
        self,
        coord1: Tuple[float, float],
        coord2: Tuple[float, float],
    ) -> float:
        """
        Great-circle distance between two (longitude, latitude) points in km.
        """
        lon1, lat1 = coord1
        lon2, lat2 = coord2
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return EARTH_RADIUS_KM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def nearest_feature(
        self,
        origin: Tuple[float, float],
        features: List[Dict[str, Any]],
        coord_key: str = "geometry",
    ) -> Optional[Dict[str, Any]]:
        """
        Find the nearest feature to origin (lon, lat) from a list.
        Each feature must have a GeoJSON geometry under coord_key.
        """
        if not features:
            return None

        best = None
        best_dist = float("inf")

        for f in features:
            geom = f.get(coord_key, {})
            coords = geom.get("coordinates")
            if not coords:
                continue
            # Support Point geometries
            if geom.get("type") == "Point":
                fcoord = (float(coords[0]), float(coords[1]))
                d = self.haversine_distance_km(origin, fcoord)
                if d < best_dist:
                    best_dist = d
                    best = {**f, "_distance_km": round(d, 3)}

        return best

    # ─── Point-in-Polygon ────────────────────────────────────────────────────

    def point_in_polygon(
        self, lon: float, lat: float, polygon_coords: List[Tuple[float, float]]
    ) -> bool:
        """
        Test whether (lon, lat) is inside a polygon defined by coordinate list.
        Uses Shapely if available, else ray-casting algorithm.
        """
        if self.available:
            try:
                point = Point(lon, lat)
                poly = Polygon(polygon_coords)
                return point.within(poly)
            except Exception as e:
                logger.warning(f"Shapely point_in_polygon failed, using ray-cast: {e}")

        # Ray-casting fallback
        n = len(polygon_coords)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon_coords[i]
            xj, yj = polygon_coords[j]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside
            j = i
        return inside

    def is_in_india_eez(self, lon: float, lat: float) -> bool:
        """Check if coordinates fall within India's approximate EEZ."""
        return self.point_in_polygon(lon, lat, INDIA_EEZ_APPROX)

    # ─── Buffer ──────────────────────────────────────────────────────────────

    def buffer_km(
        self, lon: float, lat: float, radius_km: float
    ) -> Dict[str, Any]:
        """
        Return a GeoJSON-compatible polygon representing a circular buffer.
        Uses Shapely if available (projected to degrees), else returns a bounding box.
        """
        if self.available:
            try:
                # Approximate degrees per km at this latitude
                lat_deg_per_km = 1.0 / 110.574
                lon_deg_per_km = 1.0 / (111.320 * math.cos(math.radians(lat)))
                point = Point(lon, lat)
                # Buffer in degrees (approximate for small radii)
                buf = point.buffer(radius_km * lat_deg_per_km)
                exterior = list(buf.exterior.coords)
                return {
                    "type": "Polygon",
                    "coordinates": [[(c[0], c[1]) for c in exterior]],
                }
            except Exception as e:
                logger.warning(f"Shapely buffer failed, returning bounding box: {e}")

        # Bounding box fallback
        lat_delta = radius_km / 110.574
        lon_delta = radius_km / (111.320 * math.cos(math.radians(lat)))
        return {
            "type": "Polygon",
            "coordinates": [[
                (lon - lon_delta, lat - lat_delta),
                (lon + lon_delta, lat - lat_delta),
                (lon + lon_delta, lat + lat_delta),
                (lon - lon_delta, lat + lat_delta),
                (lon - lon_delta, lat - lat_delta),
            ]],
        }

    # ─── Filter features within radius ───────────────────────────────────────

    def filter_within_radius_km(
        self,
        origin: Tuple[float, float],
        features: List[Dict[str, Any]],
        radius_km: float,
        coord_key: str = "geometry",
    ) -> List[Dict[str, Any]]:
        """
        Filter features to only those within radius_km of origin.
        Returns features sorted by distance (nearest first), each annotated with _distance_km.
        """
        result = []
        for f in features:
            geom = f.get(coord_key, {})
            coords = geom.get("coordinates")
            if not coords:
                continue
            if geom.get("type") == "Point":
                fcoord = (float(coords[0]), float(coords[1]))
                d = self.haversine_distance_km(origin, fcoord)
                if d <= radius_km:
                    result.append({**f, "_distance_km": round(d, 3)})

        return sorted(result, key=lambda x: x["_distance_km"])

    # ─── Route intersection ───────────────────────────────────────────────────

    def route_intersects_zone(
        self,
        route_coords: List[Tuple[float, float]],
        zone_polygon: List[Tuple[float, float]],
    ) -> bool:
        """
        Test whether a LineString route intersects a polygon zone.
        Uses Shapely if available.
        """
        if not self.available or len(route_coords) < 2:
            # Fallback: check if any route point is inside the zone
            return any(
                self.point_in_polygon(lon, lat, zone_polygon)
                for lon, lat in route_coords
            )
        try:
            route = LineString(route_coords)
            zone = Polygon(zone_polygon)
            return route.intersects(zone)
        except Exception as e:
            logger.warning(f"Shapely route intersection failed: {e}")
            return False

    # ─── Summary for agent state ──────────────────────────────────────────────

    def analyze_location(
        self,
        lon: float,
        lat: float,
        pfz_records: Optional[List[Dict[str, Any]]] = None,
        restricted_zones: Optional[List[Dict[str, Any]]] = None,
        search_radius_km: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive spatial analysis for an agent query.
        Returns structured analysis result for the agent state.
        """
        analysis: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coordinates": {"longitude": lon, "latitude": lat},
            "is_indian_eez": self.is_in_india_eez(lon, lat),
            "nearest_pfz": None,
            "pfz_within_radius": [],
            "restricted_zone_violations": [],
            "buffer_geojson": self.buffer_km(lon, lat, radius_km=search_radius_km),
        }

        # Find nearest PFZ
        if pfz_records:
            nearest = self.nearest_feature((lon, lat), pfz_records)
            if nearest:
                analysis["nearest_pfz"] = nearest
            analysis["pfz_within_radius"] = self.filter_within_radius_km(
                (lon, lat), pfz_records, radius_km=search_radius_km
            )

        # Check restricted zone violations
        if restricted_zones:
            for zone in restricted_zones:
                geom = zone.get("geometry", {})
                if geom.get("type") == "Polygon":
                    poly_coords = [(c[0], c[1]) for c in geom["coordinates"][0]]
                    if self.point_in_polygon(lon, lat, poly_coords):
                        analysis["restricted_zone_violations"].append(zone.get("name", "Unknown Zone"))

        return analysis


gis_service = GISService()
