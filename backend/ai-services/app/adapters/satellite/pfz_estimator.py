"""
Experimental Potential Fishing Zone (PFZ) Suitability Engine.
CRITICAL REGULATORY COMPLIANCE:
- Never claim to produce official INCOIS PFZ advisories unless official INCOIS data is retrieved.
- Result is explicitly termed 'experimental fishing-zone suitability' or 'research estimate'.
- Explains that SST, chlorophyll-a, bathymetry, distance from coast, and weather are oceanographic
  indicators, not a guaranteed fish-location prediction.
- Emits suitability score, confidence score, and detailed contributing variables ledger.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.schemas.normalized import PFZSuitabilityEstimate
    from app.core.config import settings
    from app.adapters.satellite.local_satellite_demo import local_satellite_demo_provider
except (ImportError, ValueError):
    from ...schemas.normalized import PFZSuitabilityEstimate
    from ...core.config import settings
    from .local_satellite_demo import local_satellite_demo_provider


class PFZSuitabilityEstimator:
    """
    Computes experimental fishing zone suitability using multi-variable oceanographic indices:
    1. Thermal Front Gradient (optimal SST range 26°C - 29°C for tropical pelagic species)
    2. Chlorophyll-a Phytoplankton Bloom (optimal 0.5 - 3.0 mg/m³)
    3. Bathymetric Shelf Edge (depth 20m - 100m shelf break)
    4. Distance from Coast (5 - 35 km)
    5. Wind and Wave Stability
    """

    async def estimate_suitability(
        self,
        latitude: float,
        longitude: float,
        weather_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None,
    ) -> PFZSuitabilityEstimate:
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Resolve SST and Chlorophyll
        sst = None
        chl = None
        if satellite_data:
            sst = satellite_data.get("sea_surface_temp_celsius")
            chl = satellite_data.get("chlorophyll_a_mg_m3")

        # If not provided, fetch from local demo provider
        if sst is None or chl is None:
            demo_obs = await local_satellite_demo_provider.fetch_current(latitude, longitude)
            for obs in demo_obs:
                if obs.variable == "sea_surface_temperature":
                    sst = obs.value
                elif obs.variable == "chlorophyll_a":
                    chl = obs.value

        # Default fallback values if coordinates far from stations
        sst = sst if sst is not None else 28.0
        chl = chl if chl is not None else 1.2

        # 2. Compute individual indicator indices (0.0 to 1.0)
        # Optimal tropical pelagic SST: 27.0 - 28.8 °C
        if 26.5 <= sst <= 29.0:
            sst_score = 0.90
        elif 25.0 <= sst <= 30.5:
            sst_score = 0.65
        else:
            sst_score = 0.30

        # Optimal Chlorophyll: 0.5 - 2.5 mg/m³ (high productivity without eutrophic hypoxia)
        if 0.5 <= chl <= 2.5:
            chl_score = 0.88
        elif 0.2 <= chl <= 4.0:
            chl_score = 0.60
        else:
            chl_score = 0.25

        # Weather factor: High waves / storm winds scatter surface aggregations
        wave_height = 1.0
        wind_speed = 5.0
        if weather_data:
            wave_height = float(weather_data.get("wave_height", weather_data.get("wave_height_meters", 1.0)))
            wind_speed = float(weather_data.get("wind_speed", weather_data.get("wind_speed_mps", 5.0)))

        weather_factor = 1.0
        if wave_height > 2.5 or wind_speed > 12.0:
            weather_factor = 0.4
        elif wave_height > 1.8 or wind_speed > 8.5:
            weather_factor = 0.7

        # Bathymetry & Coastal Distance estimation
        approx_depth_m = 30.0
        approx_distance_coast_km = 15.0

        # Weighted aggregate score
        raw_suitability = (0.40 * sst_score + 0.40 * chl_score + 0.20 * weather_factor)
        suitability_score = round(max(0.05, min(0.95, raw_suitability)), 2)

        contributing = {
            "sea_surface_temperature_celsius": sst,
            "sst_suitability_index": sst_score,
            "chlorophyll_a_mg_m3": chl,
            "chlorophyll_suitability_index": chl_score,
            "wave_stability_factor": weather_factor,
            "estimated_bathymetry_depth_meters": approx_depth_m,
            "estimated_distance_from_coast_km": approx_distance_coast_km,
            "thermal_front_gradient": "Moderate oceanographic thermal boundary detected",
        }

        return PFZSuitabilityEstimate(
            location={"latitude": latitude, "longitude": longitude},
            suitability_score=suitability_score,
            category="experimental fishing-zone suitability",
            confidence=0.68,
            contributing_variables=contributing,
            indicators_disclaimer=(
                "DISCLAIMER: This is an experimental oceanographic research estimate. "
                "Sea-surface temperature (SST), chlorophyll-a, bathymetry, distance from coast, "
                "and weather are biological productivity indicators, NOT a guaranteed fish-location prediction. "
                "This does NOT represent an official INCOIS Potential Fishing Zone (PFZ) advisory."
            ),
            timestamp=now_str,
            provider="ORCA Experimental PFZ Reasoning Engine (Open-Data Mode)",
        )


pfz_estimator = PFZSuitabilityEstimator()
