"""
Standardized Marine, Weather, Ocean, Tide, and Fishing Zone Schemas for ORCA.
Strict Pydantic contracts ensuring normalization across all external open data providers.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Geographic coordinate representation."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    name: Optional[str] = Field(default=None, description="Resolved place name or coastal feature")


class WeatherData(BaseModel):
    """Normalized atmospheric meteorological parameters."""
    temperature: Optional[float] = Field(None, description="Air temperature in Celsius")
    apparent_temperature: Optional[float] = Field(None, description="Apparent / heat index temperature in Celsius")
    wind_speed: Optional[float] = Field(None, description="Wind speed in meters per second (m/s)")
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees from true North")
    wind_gusts: Optional[float] = Field(None, description="Peak wind gusts in meters per second (m/s)")
    precipitation: Optional[float] = Field(None, description="Precipitation rate in millimeters (mm)")
    pressure: Optional[float] = Field(None, description="Surface barometric pressure in hPa")
    humidity: Optional[float] = Field(None, description="Relative humidity in percentage (%)")
    cloud_cover: Optional[float] = Field(None, description="Cloud area fraction percentage (%)")
    visibility: Optional[float] = Field(None, description="Horizontal visibility in meters or km")
    weather_code: Optional[int] = Field(None, description="WMO weather interpretation code")


class MarineData(BaseModel):
    """Normalized ocean surface and sea-state parameters."""
    wave_height: Optional[float] = Field(None, description="Significant wave height in meters")
    wave_direction: Optional[float] = Field(None, description="Dominant wave direction in degrees")
    wave_period: Optional[float] = Field(None, description="Dominant wave period in seconds")
    swell_wave_height: Optional[float] = Field(None, description="Primary swell wave height in meters")
    swell_wave_direction: Optional[float] = Field(None, description="Primary swell wave direction in degrees")
    swell_wave_period: Optional[float] = Field(None, description="Primary swell wave period in seconds")
    sea_surface_temperature: Optional[float] = Field(None, description="Sea Surface Temperature (SST) in Celsius")
    ocean_current_velocity: Optional[float] = Field(None, description="Surface current velocity in m/s")
    ocean_current_direction: Optional[float] = Field(None, description="Surface current direction in degrees")
    sea_level: Optional[float] = Field(None, description="Sea surface height above MSL in meters")


class OceanBiology(BaseModel):
    """Normalized ocean color and biogeochemical parameters."""
    chlorophyll: Optional[float] = Field(None, description="Chlorophyll-a concentration in mg/m³")
    salinity: Optional[float] = Field(None, description="Practical Salinity Units (PSU)")
    dissolved_oxygen: Optional[float] = Field(None, description="Dissolved oxygen in mmol/m³")
    turbidity: Optional[float] = Field(None, description="Water clarity / turbidity index")


class DataSource(BaseModel):
    """Attribution and provenance metadata for each contributing provider."""
    provider: str = Field(..., description="Provider name e.g. open_meteo, met_no, incois_erddap, copernicus")
    dataset: Optional[str] = Field(None, description="Specific dataset identifier or model")
    timestamp: Optional[str] = Field(None, description="Timestamp when observation/forecast was recorded")
    retrieved_at: Optional[str] = Field(None, description="Timestamp when ORCA retrieved the data")
    confidence: Optional[float] = Field(default=0.9, ge=0.0, le=1.0, description="Estimated data confidence")
    data_status: str = Field(default="fresh", description="fresh, stale, or unavailable")
    freshness_minutes: Optional[int] = Field(default=0, description="Age of data in minutes")
    source_url: Optional[str] = Field(None, description="Official endpoint or portal documentation URL")


class MarineObservation(BaseModel):
    """Comprehensive normalized multi-domain marine and meteorological observation."""
    location: Location
    timestamp: str = Field(..., description="Observation validity timestamp (ISO-8601 UTC)")
    weather: Optional[WeatherData] = None
    marine: Optional[MarineData] = None
    biology: Optional[OceanBiology] = None
    sources: List[DataSource] = Field(default_factory=list)
    status: str = Field(default="available", description="available, partial, or unavailable")


class TideData(BaseModel):
    """Normalized tide and water-level information."""
    station: str = Field(default="Open-Ocean Water Level", description="Station name or geographic reference")
    station_id: str = Field(default="water-level-grid", description="Station identifier")
    water_level: Optional[float] = Field(None, description="Water level height in meters")
    datum: str = Field(default="Mean Sea Level (MSL)", description="Vertical datum (MSL or Chart Datum)")
    timestamp: str = Field(..., description="Observation / forecast timestamp (ISO-8601 UTC)")
    provider: str = Field(..., description="Source provider name")
    data_status: str = Field(default="estimated", description="observation, prediction, estimated, or unavailable")
    source_url: str = Field(default="", description="Provider URL")
    is_official_tide_table: bool = Field(default=False, description="True ONLY if verified hydrographic tide table")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional station or proxy details")


class FishingZone(BaseModel):
    """Potential Fishing Zone candidate zone."""
    id: str = Field(..., description="Unique zone identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="Suitability score 0-100")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Scientific confidence 0-1.0")
    sst_celsius: Optional[float] = Field(None, description="Sea Surface Temperature in Celsius")
    chlorophyll_mg_m3: Optional[float] = Field(None, description="Chlorophyll-a concentration in mg/m³")
    current_velocity_mps: Optional[float] = Field(None, description="Ocean current velocity in m/s")
    distance_km: Optional[float] = Field(None, description="Approximate distance from nearest landing center")
    is_official_incois: bool = Field(default=False, description="True ONLY if retrieved from official INCOIS PFZ")
    zone_type: str = Field(default="AI-derived candidate fishing zone", description="Advisory classification")
    explanation: str = Field(default="", description="Oceanographic reasoning explaining the candidate zone")
    valid_from: str = Field(default="", description="Validity start time")
    valid_to: str = Field(default="", description="Validity end time")
    sources: List[DataSource] = Field(default_factory=list)
