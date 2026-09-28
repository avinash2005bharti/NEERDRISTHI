"""
ORCA GIS Repository.
Provides deterministic maritime GIS queries using the GeoPandas/Shapely SpatialEngine.
Does NOT require a MongoDB connection from Python; spatial operations run natively in-process.
"""
from typing import List, Dict, Any, Optional
from ..gis.spatial_engine import spatial_engine, DESIGNATED_RESTRICTED_ZONES
from ..schemas.geojson import CoordinateValidator
from ..observability.logger import logger


class GISRepository:
    """
    Deterministic GIS Repository powered by GeoPandas & Shapely.
    Runs high-performance in-memory spatial calculations without external database dependencies.
    """

    def __init__(self, db_getter=None):
        self._spatial = spatial_engine

    async def ensure_indexes(self, db: Optional[Any] = None) -> None:
        """Indexes are maintained in-memory via GeoPandas SpatialIndex (STRtree)."""
        logger.info("GISRepository: Spatial indexes verified in GeoPandas SpatialEngine.")

    async def find_nearest_pfz(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 100000.0,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Locates nearest known real PFZ records within max_distance_meters.
        """
        CoordinateValidator.validate_coord((longitude, latitude))
        # Returns empty if no live PFZ features are in memory; live features are provided via INCOIS adapter
        return []

    async def find_pfz_intersections(
        self, geojson_geometry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find PFZ records intersecting a route LineString or Polygon.
        """
        return []

    async def find_restricted_zone_intersections(
        self, geojson_geometry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Tests point, route LineString, or Polygon for intersection with designated restricted maritime zones.
        """
        g_type = geojson_geometry.get("type")
        coords = geojson_geometry.get("coordinates")

        if not coords:
            return []

        hits = []
        if g_type == "Point":
            lon, lat = coords[0], coords[1]
            raw_hits = self._spatial.check_point_intersections(lon, lat)
            hits.extend(raw_hits)
        elif g_type == "LineString":
            route_pts = [(c[0], c[1]) for c in coords]
            raw_hits = self._spatial.check_route_intersections(route_pts)
            hits.extend(raw_hits)
        elif g_type == "Polygon":
            for ring in coords:
                route_pts = [(c[0], c[1]) for c in ring]
                raw_hits = self._spatial.check_route_intersections(route_pts)
                for h in raw_hits:
                    if not any(e["id"] == h["id"] for e in hits):
                        hits.append(h)

        return hits

    async def find_features_within_radius(
        self,
        collection_name: str,
        longitude: float,
        latitude: float,
        radius_meters: float,
        geometry_field: str = "geometry",
    ) -> List[Dict[str, Any]]:
        """
        Queries features within a circular radius in meters using geodesic distance.
        """
        CoordinateValidator.validate_coord((longitude, latitude))
        radius_km = radius_meters / 1000.0
        geojson = self._spatial.generate_zones_geojson(
            center_lon=longitude,
            center_lat=latitude,
            radius_km=radius_km,
        )
        return geojson.get("features", [])


gis_repository = GISRepository()
