from pathlib import Path
from typing import Dict, Any
import yaml
from ..schemas.safety import SafetyPolicyConfig, VesselLimits
from ..observability.logger import logger


DEFAULT_VESSEL_LIMITS: Dict[str, VesselLimits] = {
    "traditional_unmotorized": VesselLimits(
        max_wave_height_meters=1.2,
        max_wind_speed_mps=8.0,
        description="Traditional non-motorized craft",
    ),
    "motorized_fiberglass": VesselLimits(
        max_wave_height_meters=2.0,
        max_wind_speed_mps=12.5,
        description="Fiberglass boats with outboard motor",
    ),
    "mechanized_trawler": VesselLimits(
        max_wave_height_meters=3.5,
        max_wind_speed_mps=18.0,
        description="Mechanized trawler",
    ),
    "deep_sea_vessel": VesselLimits(
        max_wave_height_meters=5.0,
        max_wind_speed_mps=22.0,
        description="Large deep-sea vessel",
    ),
}


def load_safety_policy(policy_path: str = None) -> SafetyPolicyConfig:
    if policy_path is None:
        policy_path = str(Path(__file__).parent / "policy.yaml")

    path = Path(policy_path)
    if not path.is_file():
        logger.warning(f"Safety policy file not found at {path}, using safe built-in defaults.")
        return SafetyPolicyConfig(
            version="1.0.0-fallback",
            vessel_limits=DEFAULT_VESSEL_LIMITS,
            severe_weather_warning_action="NO_GO",
            missing_weather_action="INSUFFICIENT_DATA",
            missing_marine_action="INSUFFICIENT_DATA",
            restricted_zone_action="NO_GO",
            stale_data_action="GO_WITH_CAUTION",
            default_action_on_critical_gap="INSUFFICIENT_DATA",
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data: Dict[str, Any] = yaml.safe_load(f)

        vessel_limits = {}
        for k, v in raw_data.get("vessel_limits", {}).items():
            vessel_limits[k] = VesselLimits(
                max_wave_height_meters=float(v.get("max_wave_height_meters", 2.0)),
                max_wind_speed_mps=float(v.get("max_wind_speed_mps", 12.0)),
                description=v.get("description", k),
            )

        return SafetyPolicyConfig(
            version=raw_data.get("version", "1.0.0"),
            vessel_limits=vessel_limits,
            severe_weather_warning_action=raw_data.get("severe_weather_warning_action", "NO_GO"),
            missing_weather_action=raw_data.get("missing_weather_action", "INSUFFICIENT_DATA"),
            missing_marine_action=raw_data.get("missing_marine_action", "INSUFFICIENT_DATA"),
            restricted_zone_action=raw_data.get("restricted_zone_action", "NO_GO"),
            stale_data_action=raw_data.get("stale_data_action", "GO_WITH_CAUTION"),
            default_action_on_critical_gap=raw_data.get("default_action_on_critical_gap", "INSUFFICIENT_DATA"),
        )
    except Exception as e:
        logger.error(f"Failed to parse safety policy from {path}: {e}. Falling back to default policy.")
        return SafetyPolicyConfig(
            version="1.0.0-fallback",
            vessel_limits=DEFAULT_VESSEL_LIMITS,
            severe_weather_warning_action="NO_GO",
            missing_weather_action="INSUFFICIENT_DATA",
            missing_marine_action="INSUFFICIENT_DATA",
            restricted_zone_action="NO_GO",
            stale_data_action="GO_WITH_CAUTION",
            default_action_on_critical_gap="INSUFFICIENT_DATA",
        )


safety_policy = load_safety_policy()
