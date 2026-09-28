from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .contracts import SafetyRecommendation, RiskLevel


class VesselLimits(BaseModel):
    max_wave_height_meters: float
    max_wind_speed_mps: float
    description: str


class SafetyPolicyConfig(BaseModel):
    version: str
    vessel_limits: Dict[str, VesselLimits]
    severe_weather_warning_action: SafetyRecommendation
    missing_weather_action: SafetyRecommendation
    missing_marine_action: SafetyRecommendation
    restricted_zone_action: SafetyRecommendation
    stale_data_action: SafetyRecommendation
    default_action_on_critical_gap: SafetyRecommendation


class RiskEvaluationResult(BaseModel):
    recommendation: SafetyRecommendation
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    triggered_rules: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    required_next_action: str
    evidence_references: List[str] = Field(default_factory=list)
