from typing import Optional, Dict, Any, List
from .policy import safety_policy
from ..schemas.safety import RiskEvaluationResult, VesselLimits
from ..schemas.contracts import SafetyRecommendation, RiskLevel


class SafetyRiskEngine:
    """
    Deterministic maritime safety & risk engine.
    This module executes pure algorithmic rules based on official physical limits.
    It never relies on LLM heuristics to determine safety.
    """

    def __init__(self, policy=safety_policy):
        self.policy = policy

    def evaluate(
        self,
        vessel_class: Optional[str],
        weather_data: Optional[Dict[str, Any]],
        marine_data: Optional[Dict[str, Any]],
        geospatial_data: Optional[Dict[str, Any]],
        data_availability: Dict[str, str],
        evidence_list: Optional[List[Dict[str, Any]]] = None,
    ) -> RiskEvaluationResult:
        triggered_rules: List[str] = []
        missing_data: List[str] = []
        evidence_refs: List[str] = []

        # 1. Resolve vessel limits
        normalized_vessel = (vessel_class or "motorized_fiberglass").lower()
        vessel_limit: VesselLimits = self.policy.vessel_limits.get(
            normalized_vessel,
            self.policy.vessel_limits.get("motorized_fiberglass")
        )

        # 2. Check Critical Data Availability
        is_weather_available = (data_availability.get("weather") == "available")
        is_weather_stale = (data_availability.get("weather") == "stale")

        if not is_weather_available and not is_weather_stale:
            missing_data.append("Live Weather & Sea-State Telemetry (Wind speed, Wave height)")
        if data_availability.get("marine") == "unavailable":
            missing_data.append("INCOIS Ocean State / PFZ Bulletin")

        # CRITICAL SAFETY REQUIREMENT:
        # If live weather/sea-state telemetry is completely unavailable, policy mandates INSUFFICIENT_DATA or NO_GO.
        # It must NEVER declare safe.
        if missing_data and not is_weather_available:
            triggered_rules.append(
                f"Missing critical telemetry policy: Weather/sea-state data unavailable. Defaulting to {self.policy.missing_weather_action}"
            )
            return RiskEvaluationResult(
                recommendation=self.policy.missing_weather_action,
                risk_level="UNKNOWN",
                risk_score=75,
                confidence_score=15,
                triggered_rules=triggered_rules,
                missing_data=missing_data,
                required_next_action=(
                    "Do NOT venture out to sea without verified local port meteorological clearance. "
                    "Awaiting official IMD/INCOIS feed connectivity."
                ),
                evidence_references=evidence_refs,
            )

        # 3. Assess Restricted Zone Infringements
        restricted_hits = []
        if geospatial_data and geospatial_data.get("restricted_zone_intersections"):
            restricted_hits = geospatial_data["restricted_zone_intersections"]
            for zone in restricted_hits:
                zone_name = zone.get("name", "Designated Restricted Maritime Zone")
                triggered_rules.append(
                    f"Route or target point intersects with restricted maritime boundary: '{zone_name}'"
                )

        if restricted_hits:
            return RiskEvaluationResult(
                recommendation="NO_GO",
                risk_level="CRITICAL",
                risk_score=95,
                confidence_score=90,
                triggered_rules=triggered_rules,
                missing_data=missing_data,
                required_next_action="Re-route immediately away from restricted / international maritime boundary zones.",
                evidence_references=["geospatial_restricted_zones"],
            )

        # 4. Severe Weather Warnings
        warning_flag = None
        if weather_data:
            warning_flag = weather_data.get("warning_flag")

        if warning_flag:
            triggered_rules.append(f"Official Severe Weather Alert Active: '{warning_flag}'")
            return RiskEvaluationResult(
                recommendation="NO_GO",
                risk_level="CRITICAL",
                risk_score=90,
                confidence_score=95,
                triggered_rules=triggered_rules,
                missing_data=missing_data,
                required_next_action="All fishing operations suspended. Remain in harbor or return to nearest shore shelter immediately.",
                evidence_references=["weather_warning_flag"],
            )

        # 5. Physical Threshold Evaluation (Wave Height & Wind Speed)
        wave_height = float(weather_data.get("wave_height_meters", 0.0)) if weather_data else 0.0
        wind_speed = float(weather_data.get("wind_speed_mps", 0.0)) if weather_data else 0.0
        is_stale = is_weather_stale or (weather_data and weather_data.get("freshness") == "stale")

        recommendation: SafetyRecommendation = "GO"
        risk_level: RiskLevel = "LOW"
        risk_score = 15
        confidence = 85

        # Check wave height against vessel class threshold
        if wave_height > vessel_limit.max_wave_height_meters:
            triggered_rules.append(
                f"Significant wave height ({wave_height:.2f}m) exceeds safe threshold ({vessel_limit.max_wave_height_meters:.2f}m) for {vessel_limit.description}"
            )
            recommendation = "NO_GO"
            risk_level = "HIGH"
            risk_score = max(risk_score, 80)
        elif wave_height > (vessel_limit.max_wave_height_meters * 0.8):
            triggered_rules.append(
                f"Significant wave height ({wave_height:.2f}m) is near cautionary limit ({vessel_limit.max_wave_height_meters * 0.8:.2f}m) for {vessel_limit.description}"
            )
            recommendation = "GO_WITH_CAUTION"
            risk_level = "MODERATE"
            risk_score = max(risk_score, 50)

        # Check wind speed against vessel class threshold
        if wind_speed > vessel_limit.max_wind_speed_mps:
            triggered_rules.append(
                f"Wind speed ({wind_speed:.1f} m/s) exceeds maximum safe operating wind ({vessel_limit.max_wind_speed_mps:.1f} m/s) for {vessel_limit.description}"
            )
            recommendation = "NO_GO"
            risk_level = "HIGH"
            risk_score = max(risk_score, 85)
        elif wind_speed > (vessel_limit.max_wind_speed_mps * 0.8):
            triggered_rules.append(
                f"Wind speed ({wind_speed:.1f} m/s) is approaching cautionary limits for {vessel_limit.description}"
            )
            if recommendation != "NO_GO":
                recommendation = "GO_WITH_CAUTION"
                risk_level = "MODERATE"
            risk_score = max(risk_score, 55)

        # Stale data penalty
        if is_stale:
            triggered_rules.append("Telemetry data is older than configured freshness limit; proceed with caution.")
            if recommendation == "GO":
                recommendation = "GO_WITH_CAUTION"
            confidence -= 25
            risk_score = min(100, risk_score + 15)

        # Required next action formulation
        if recommendation == "NO_GO":
            action = "Venture cancelled. Maintain vessel docked or seek protected anchorage immediately."
        elif recommendation == "GO_WITH_CAUTION":
            action = "Equip mandatory VHF marine radio and lifejackets. Stay within 5 NM of coastline and monitor VHF Ch 16."
        elif recommendation == "GO":
            action = "Conditions favorable within safe vessel parameters. Log trip departure with coastal fisheries station."
        else:
            action = "Await fresh telemetry observations before departing."

        return RiskEvaluationResult(
            recommendation=recommendation,
            risk_level=risk_level,
            risk_score=min(100, max(0, risk_score)),
            confidence_score=min(100, max(0, confidence)),
            triggered_rules=triggered_rules,
            missing_data=missing_data,
            required_next_action=action,
            evidence_references=evidence_refs,
        )


safety_engine = SafetyRiskEngine()
