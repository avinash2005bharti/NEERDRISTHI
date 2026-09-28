from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..schemas.geojson import CoordinateValidator
from ..integrations.geocoder_adapter import geocoder_adapter
from ..repositories.gis_repository import gis_repository
from ..services.gis_service import gis_service
from ..utils.geo import is_indian_ocean_region
from ..observability.logger import logger


class GeospatialAgent:
    """
    Geospatial Agent.
    Resolves place coordinates via Nominatim, runs MongoDB 2dsphere spatial operations,
    and uses Shapely/GeoPandas for deterministic GIS intersection and buffer calculations.
    The LLM is NEVER involved in spatial reasoning.
    """

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        location = state.get("location") or {}
        route = state.get("route")
        evidence = list(state.get("evidence") or [])
        data_availability: Dict[str, str] = {}

        lat = location.get("latitude")
        lon = location.get("longitude")
        resolved_coords: Optional[Tuple[float, float]] = None

        # 1. Resolve coordinates — direct input or Nominatim geocoding
        if lat is not None and lon is not None:
            try:
                CoordinateValidator.validate_coord((lon, lat))
                resolved_coords = (lon, lat)
            except Exception as e:
                logger.warning(f"Invalid coordinate bounds: {e}")
        elif location.get("name"):
            geo_res = await geocoder_adapter.resolve_place_name(location["name"])
            if hasattr(geo_res, "latitude"):
                resolved_coords = (geo_res.longitude, geo_res.latitude)
                logger.info(f"Geocoded '{location['name']}' → {resolved_coords}")

        geospatial_data: Dict[str, Any] = {
            "resolved_coordinates": list(resolved_coords) if resolved_coords else None,
            "restricted_zone_intersections": [],
            "nearest_pfz_zones": [],
            "is_marine_region": False,
            "is_india_eez": False,
        }

        if resolved_coords:
            lon_r, lat_r = resolved_coords
            data_availability["geospatial"] = "available"

            # 2. Broader marine region check
            is_marine = is_indian_ocean_region(lon_r, lat_r)
            is_eez = gis_service.is_in_india_eez(lon_r, lat_r)
            geospatial_data["is_marine_region"] = is_marine
            geospatial_data["is_india_eez"] = is_eez

            # 3. MongoDB 2dsphere restricted zone query
            point_geom = {"type": "Point", "coordinates": [lon_r, lat_r]}
            restricted_hits = await gis_repository.find_restricted_zone_intersections(point_geom)

            # 4. Route intersection (MongoDB 2dsphere + Shapely double-check)
            if route and route.get("type") == "LineString":
                route_coords = route.get("coordinates", [])
                route_hits = await gis_repository.find_restricted_zone_intersections(route)
                restricted_hits.extend(route_hits)

                # Shapely-based route intersection for zones loaded from MongoDB
                if route_coords and gis_service.available:
                    try:
                        all_zones = await gis_repository.find_features_within_radius(
                            "restricted_zones", lon_r, lat_r, radius_meters=200_000
                        )
                        for zone in all_zones:
                            geom = zone.get("geometry", {})
                            if geom.get("type") == "Polygon":
                                zone_poly = [(c[0], c[1]) for c in geom["coordinates"][0]]
                                route_pts = [(c[0], c[1]) for c in route_coords]
                                if gis_service.route_intersects_zone(route_pts, zone_poly):
                                    if zone not in restricted_hits:
                                        restricted_hits.append(zone)
                    except Exception as e:
                        logger.warning(f"Shapely route intersection failed: {e}")

            geospatial_data["restricted_zone_intersections"] = [
                {"name": z.get("name", "Restricted Zone"), "zone_type": z.get("zone_type", "restricted")}
                for z in restricted_hits
            ]

            # 5. Add evidence for each restricted zone hit
            for hit in restricted_hits:
                evidence.append({
                    "category": "geospatial",
                    "name": "Restricted Maritime Zone Infringement",
                    "value": hit.get("name", "Designated Restricted Boundary"),
                    "observedAt": None,
                    "validUntil": None,
                    "retrievedAt": datetime.now(timezone.utc).isoformat(),
                    "sourceName": "National Maritime Boundary Register",
                    "sourceUrl": None,
                    "freshness": "fresh",
                })

            # 6. Nearest PFZ from MongoDB
            nearest_pfz = await gis_repository.find_nearest_pfz(lon_r, lat_r, max_distance_meters=100_000.0)
            geospatial_data["nearest_pfz_zones"] = nearest_pfz

            # 7. GIS analysis summary (for synthesis agent)
            geospatial_data["gis_analysis"] = gis_service.analyze_location(
                lon=lon_r,
                lat=lat_r,
                search_radius_km=100.0,
            )

        else:
            data_availability["geospatial"] = "unavailable"

        trace_entry = {
            "agent": "geospatial",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"Coordinates resolved: {resolved_coords is not None} | "
                f"EEZ: {geospatial_data.get('is_india_eez')} | "
                f"Restricted zones: {len(geospatial_data['restricted_zone_intersections'])} | "
                f"GIS engine: {'shapely' if gis_service.available else 'haversine'}"
            ),
        }
        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "resolved_coordinates": resolved_coords,
            "geospatial_data": geospatial_data,
            "evidence": evidence,
            "data_availability": data_availability,
            "agent_traces": current_traces,
        }


geospatial_agent = GeospatialAgent()
