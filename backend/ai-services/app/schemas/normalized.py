"""
Normalized Data Contracts for ORCA SIH26176.
Enforces strict Pydantic schemas across all weather, marine, tide, satellite, alert, and safety providers.
"""
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field


class WeatherForecast(BaseModel):
    """Normalized weather forecast schema."""
    location: str = Field(default="Unknown", description="Resolved location name or coordinate description")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    timezone: str = Field(default="UTC")
    issued_at: str
    valid_from: str
    valid_to: str
    hourly_values: Dict[str, List[Any]] = Field(default_factory=dict)
    units: Dict[str, str] = Field(default_factory=dict)
    provider: str
    source_url: str
    data_status: str = Field(..., description="forecast, observation, historical, delayed, or unavailable")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class MarineForecast(BaseModel):
    """Normalized marine sea-state forecast schema."""
    location: str = Field(default="Unknown")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    issued_at: str
    valid_from: str
    valid_to: str
    wave_height: float = Field(..., description="Significant wave height in meters")
    wave_period: Optional[float] = Field(None, description="Dominant wave period in seconds")
    wave_direction: Optional[float] = Field(None, description="Dominant wave direction in degrees")
    wind_speed: float = Field(..., description="Wind speed in meters per second")
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees")
    current_speed: Optional[float] = Field(None, description="Ocean current velocity in m/s")
    current_direction: Optional[float] = Field(None, description="Ocean current direction in degrees")
    sea_level: Optional[float] = Field(None, description="Sea surface height / level in meters")
    units: Dict[str, str] = Field(default_factory=dict)
    provider: str
    source_url: str
    data_status: str = Field(..., description="forecast, observation, historical, delayed, or unavailable")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class TideObservation(BaseModel):
    """Normalized tide and water-level observation/prediction schema."""
    station: str = Field(..., description="Tide gauge station name")
    station_id: str = Field(..., description="Unique station identifier")
    observed_or_predicted: str = Field(..., description="predicted, observed, or estimated")
    timestamp: str
    water_level: Optional[float] = Field(None, description="Water level in meters")
    datum: str = Field(default="Chart Datum (CD)")
    units: str = Field(default="meters")
    provider: str
    source_url: str
    data_status: str = Field(..., description="observation, prediction, estimated, or DATA_UNAVAILABLE")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class SatelliteObservation(BaseModel):
    """Normalized satellite ocean-color and SST observation schema."""
    variable: str = Field(..., description="sea_surface_temperature, chlorophyll_a, etc.")
    value: Optional[float] = Field(None, description="Numeric measured value")
    units: str = Field(default="celsius")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    observation_time: str
    product_time: str
    resolution: str = Field(default="1km")
    dataset: str
    provider: str
    source_url: str
    data_status: str = Field(..., description="observation, near_real_time, historical, demo, or unavailable")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class MarineAlert(BaseModel):
    """Normalized official marine weather or cyclone alert."""
    alert_id: str
    issuing_agency: str
    event_type: str
    severity: str = Field(..., description="Extreme, Severe, Moderate, Minor, or Unknown")
    urgency: str = Field(default="Immediate")
    certainty: str = Field(default="Observed")
    affected_area: str
    issue_time: str
    expiry_time: Optional[str] = None
    instruction: str
    official_url: str


class PFZSuitabilityEstimate(BaseModel):
    """Experimental Potential Fishing Zone (PFZ) suitability estimate."""
    location: Dict[str, float] = Field(..., description="dict with latitude, longitude")
    suitability_score: float = Field(..., ge=0.0, le=1.0, description="0.0 to 1.0 suitability score")
    category: str = Field(default="experimental fishing-zone suitability")
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    contributing_variables: Dict[str, Any] = Field(default_factory=dict)
    indicators_disclaimer: str = Field(
        default="SST, chlorophyll-a, thermal gradient, bathymetry, and weather are research indicators, not a guaranteed fish-location prediction."
    )
    timestamp: str
    provider: str


class SafetyAssessment(BaseModel):
    """Deterministic safety assessment schema."""
    decision: str = Field(..., description="GO, CAUTION, NO_GO, or DATA_UNAVAILABLE")
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, CRITICAL, or UNKNOWN")
    valid_time: str
    location: Dict[str, float] = Field(..., description="dict with latitude, longitude")
    reasons: List[str] = Field(default_factory=list)
    weather_evidence: Dict[str, Any] = Field(default_factory=dict)
    marine_evidence: Dict[str, Any] = Field(default_factory=dict)
    tide_evidence: Dict[str, Any] = Field(default_factory=dict)
    alert_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    official_sources: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Advisory notice: This automated assessment is an experimental decision-support aid. Never present an AI-generated recommendation as an official emergency warning. Always heed official IMD/Coast Guard instructions."
    )
    generated_at: str
    explanations: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Multilingual explanations in English ('en'), Hindi ('hi'), and Marathi ('mr')"
    )
