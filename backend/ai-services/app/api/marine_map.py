"""
Marine Map API Endpoints for ORCA (SIH26176).
Provides GeoJSON standardized spatial overlays for HD interactive marine maps.
All layers support viewport bounding boxes (bbox), spot coordinates (lat, lon, latitude, longitude), and zoom level.
"""
from typing import Optional, Tuple
from fastapi import APIRouter, Query

from ..services.marine_data import marine_provider_manager

router = APIRouter(tags=["Marine Map & Overlays"])


def parse_bbox(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """Parse comma-separated bbox: min_lon,min_lat,max_lon,max_lat."""
    if not bbox_str:
        return None
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) == 4:
            return (parts[0], parts[1], parts[2], parts[3])
    except (ValueError, TypeError):
        pass
    return None


def resolve_coords(
    lat: Optional[float],
    latitude: Optional[float],
    lon: Optional[float],
    longitude: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """Harmonizes lat/latitude and lon/longitude query parameters."""
    final_lat = lat if lat is not None else latitude
    final_lon = lon if lon is not None else longitude
    return final_lat, final_lon


@router.get("/api/marine/map/config")
@router.get("/internal/ai/marine/map/config")
async def get_map_config():
    """
    Returns map metadata, base tile definitions, layer configurations,
    and provider operational status.
    """
    return marine_provider_manager.get_map_config()


@router.get("/api/marine/sst")
@router.get("/internal/ai/marine/map/sst")
async def get_marine_sst(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Sea Surface Temperature (SST) thermal front layer as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_sst(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/chlorophyll")
@router.get("/internal/ai/marine/map/chlorophyll")
async def get_marine_chlorophyll(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Chlorophyll-a ocean color and biological productivity layer as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_chlorophyll(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/waves")
@router.get("/internal/ai/marine/map/waves")
async def get_marine_waves(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Wave height, period, direction, and swell layer as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_waves(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/wind")
@router.get("/internal/ai/marine/map/wind")
async def get_marine_wind(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Wind velocity vectors (speed, direction, gusts) as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_wind(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/tides")
@router.get("/internal/ai/marine/map/tides")
async def get_marine_tides(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    time: Optional[str] = Query(None),
):
    """
    Tidal water-level context, harmonic predictions, and nearest station status.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    return await marine_provider_manager.get_tides(
        lat=c_lat if c_lat is not None else 18.98,
        lon=c_lon if c_lon is not None else 72.82,
        time_param=time,
    )


@router.get("/api/marine/weather")
@router.get("/internal/ai/marine/map/weather")
async def get_marine_weather_spot(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
):
    """
    Real-time marine weather, sea-level temperature, and visibility.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    return await marine_provider_manager.get_weather(
        lat=c_lat if c_lat is not None else 18.98,
        lon=c_lon if c_lon is not None else 72.82,
    )


@router.get("/api/marine/pfz")
@router.get("/internal/ai/marine/map/pfz")
async def get_marine_pfz_map(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Potential Fishing Zones (PFZ) advisory polygons with confidence ratings as GeoJSON.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_pfz(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/risk")
@router.get("/internal/ai/marine/map/risk")
async def get_marine_risk_map(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    zoom: Optional[int] = Query(None, ge=1, le=20),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    """
    Marine safety hazard zones, shoals, and high swell corridors as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_risk(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, time_param=start_time or end_time
    )


@router.get("/api/marine/overview")
@router.get("/internal/ai/marine/map/overview")
async def get_marine_overview(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
):
    """
    Unified marine conditions snapshot at point (weather, waves, SST, PFZ distance, risk).
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    return await marine_provider_manager.get_overview(
        lat=c_lat if c_lat is not None else 18.98,
        lon=c_lon if c_lon is not None else 72.82,
    )


@router.get("/api/marine/zones")
@router.get("/internal/ai/marine/map/zones")
async def get_marine_zones_map(
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, description="Radial distance filter"),
):
    """
    Restricted & Security Maritime Zones (IMBL, offshore oil, naval ranges, biospheres) as GeoJSON FeatureCollection.
    """
    c_lat, c_lon = resolve_coords(lat, latitude, lon, longitude)
    parsed_bbox = parse_bbox(bbox)
    return await marine_provider_manager.get_restricted_zones(
        bbox=parsed_bbox, lat=c_lat, lon=c_lon, radius_km=radius_km
    )
