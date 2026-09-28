from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from .geojson import PointGeometry, PolygonGeometry


class DataUnavailableResult(BaseModel):
    category: str
    provider_name: str
    reason: str
    is_configured: bool = False
    details: Optional[Dict[str, Any]] = None


class PFZRecord(BaseModel):
    id: str
    geometry: Union[PointGeometry, PolygonGeometry]
    sst_celsius: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    depth_meters: Optional[float] = None
    bearing_degrees: Optional[float] = None
    distance_km: Optional[float] = None
    valid_from: str
    valid_to: str
    source_url: Optional[str] = None
    provider: str = "INCOIS"
    retrieved_at: str


class WeatherObservation(BaseModel):
    latitude: float
    longitude: float
    observed_at: str
    valid_until: Optional[str] = None
    wind_speed_mps: float = Field(..., description="Wind speed in meters per second")
    wind_gust_mps: Optional[float] = Field(None, description="Wind gusts in meters per second")
    wind_direction_degrees: Optional[float] = None
    wave_height_meters: float = Field(..., description="Significant wave height in meters")
    wave_period_seconds: Optional[float] = None
    swell_height_meters: Optional[float] = None
    precipitation_mm: float = Field(0.0, description="Precipitation in millimeters")
    sea_surface_temp_celsius: Optional[float] = None
    visibility_km: Optional[float] = None
    warning_flag: Optional[str] = None
    provider: str
    source_url: Optional[str] = None
    retrieved_at: str
    from_cache: bool = False  # True when data was served from Valkey cache


class TideObservation(BaseModel):
    station_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    observed_at: str
    tide_height_meters: float = Field(..., description="Tide level in meters relative to chart datum")
    tide_type: Optional[str] = Field(None, description="'high' or 'low' or 'current'")
    provider: str
    source_url: Optional[str] = None
    retrieved_at: str


class GeocodedLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    confidence: float = 1.0
    bounding_box: Optional[List[float]] = None
    provider: str
