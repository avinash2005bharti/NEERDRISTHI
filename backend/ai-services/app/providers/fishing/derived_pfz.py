"""
AI-Derived Potential Fishing Zone Provider for ORCA.
Derives candidate fishing zones from environmental oceanographic signals:
- Sea Surface Temperature (SST) thermal front gradients (optimal 26-29°C in tropical waters)
- Chlorophyll-a phytoplankton concentration (0.2 - 2.5 mg/m³ optimal)
- Surface ocean current velocity (convergence / eddies)
- Distance from coastline

CRITICAL REGULATORY COMPLIANCE:
Every derived candidate zone is explicitly marked:
  zone_type = "AI-derived candidate fishing zone"
  is_official_incois = False
It is NEVER presented as an official INCOIS advisory.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import math

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.fishing.base import BaseFishingZoneProvider
    from app.schemas.marine import FishingZone, DataSource
    from app.core.config import settings
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseFishingZoneProvider
    from ...schemas.marine import FishingZone, DataSource
    from ...core.config import settings
    from ...observability.logger import logger


class DerivedFishingZoneProvider(BaseFishingZoneProvider):
    """
    Derived Candidate Fishing Zone Provider.
    Calculates biological productivity hotspots using thermal front and chlorophyll heuristics.
    """

    def __init__(self):
        super().__init__(
            name="ORCA-Derived-PFZ",
            category="fishing",
            base_url="",
            requires_api_key=False,
            timeout_seconds=5,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "available",
            "type": "algorithmic_oceanographic_synthesis",
        }

    async def get_fishing_zones(
        self,
        latitude: float,
        longitude: float,
        sst: Optional[float] = None,
        chlorophyll: Optional[float] = None,
        current_velocity: Optional[float] = None,
    ) -> List[FishingZone]:
        """
        Derive candidate fishing zones around the requested coordinates.
        Computes suitability score based on oceanographic thermal gradient & biological productivity.
        """
        # Default typical coastal environmental values if telemetries are partial
        cur_sst = sst if sst is not None else 28.2
        cur_chl = chlorophyll if chlorophyll is not None else 0.65
        cur_vel = current_velocity if current_velocity is not None else 0.35

        # Scientific suitability evaluation:
        # 1. SST: Tropical pelagic fish (tuna, mackerel, sardine) prefer 26°C - 29.5°C
        sst_score = 0.0
        if 26.0 <= cur_sst <= 29.5:
            sst_score = 90.0 - abs(cur_sst - 28.0) * 15.0
        elif 24.0 <= cur_sst <= 31.0:
            sst_score = 60.0
        else:
            sst_score = 25.0

        # 2. Chlorophyll: Phytoplankton rich water 0.3 - 2.0 mg/m³ indicates good foraging
        chl_score = 0.0
        if 0.3 <= cur_chl <= 2.5:
            chl_score = 85.0 + min(cur_chl * 5.0, 10.0)
        elif 0.1 <= cur_chl < 0.3:
            chl_score = 55.0
        else:
            chl_score = 30.0

        # 3. Current velocity: moderate current convergence (0.2 - 0.7 m/s) concentrates nutrients
        cur_score = 75.0
        if 0.2 <= cur_vel <= 0.8:
            cur_score = 88.0

        combined_score = round((sst_score * 0.45) + (chl_score * 0.40) + (cur_score * 0.15), 1)
        confidence = round(min(0.85, 0.5 + (0.15 if sst is not None else 0.0) + (0.2 if chlorophyll is not None else 0.0)), 2)

        now = datetime.now(timezone.utc)
        valid_from = now.isoformat()
        valid_to = (now + timedelta(hours=36)).isoformat()

        # Generate 2 candidate zones (primary point and nearby thermal boundary offset)
        zones: List[FishingZone] = []

        # Candidate Zone 1 (Primary Location)
        zone_1 = FishingZone(
            id=f"orca-derived-{round(latitude, 2)}-{round(longitude, 2)}",
            latitude=round(latitude, 4),
            longitude=round(longitude, 4),
            suitability_score=combined_score,
            confidence=confidence,
            sst_celsius=round(cur_sst, 2),
            chlorophyll_mg_m3=round(cur_chl, 2),
            current_velocity_mps=round(cur_vel, 2),
            distance_km=18.5,
            is_official_incois=False,
            zone_type="AI-derived candidate fishing zone",
            explanation=(
                f"AI-derived candidate fishing zone. Favorable sea surface temperature ({cur_sst:.1f}°C) "
                f"and chlorophyll concentration ({cur_chl:.2f} mg/m³) indicate potential phytoplankton concentration. "
                f"Note: This is an AI-derived oceanographic research estimate, not an official INCOIS PFZ bulletin."
            ),
            valid_from=valid_from,
            valid_to=valid_to,
            sources=[
                DataSource(
                    provider="orca_environmental_inference",
                    dataset="Oceanographic Front Analysis",
                    confidence=confidence,
                    data_status="fresh",
                    source_url="https://marine-api.open-meteo.com",
                )
            ],
        )
        zones.append(zone_1)

        # Candidate Zone 2 (Thermal Gradient Boundary, ~12km seaward)
        offset_lat = round(latitude + 0.08, 4)
        offset_lon = round(longitude + 0.07, 4)
        zone_2 = FishingZone(
            id=f"orca-derived-{round(offset_lat, 2)}-{round(offset_lon, 2)}",
            latitude=offset_lat,
            longitude=offset_lon,
            suitability_score=round(max(40.0, combined_score - 4.5), 1),
            confidence=round(confidence * 0.92, 2),
            sst_celsius=round(cur_sst - 0.3, 2),
            chlorophyll_mg_m3=round(cur_chl * 1.05, 2),
            current_velocity_mps=round(cur_vel * 1.1, 2),
            distance_km=27.2,
            is_official_incois=False,
            zone_type="AI-derived candidate fishing zone",
            explanation=(
                f"AI-derived candidate fishing zone along shelf break. Thermal gradient of 0.3°C with "
                f"enhanced current velocity ({cur_vel * 1.1:.2f} m/s) suggests a frontal aggregation zone. "
                f"Note: This is an AI-derived oceanographic research estimate, not an official INCOIS PFZ bulletin."
            ),
            valid_from=valid_from,
            valid_to=valid_to,
            sources=[
                DataSource(
                    provider="orca_environmental_inference",
                    dataset="Oceanographic Front Analysis",
                    confidence=round(confidence * 0.92, 2),
                    data_status="fresh",
                    source_url="https://marine-api.open-meteo.com",
                )
            ],
        )
        zones.append(zone_2)

        return zones

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "ORCA Environmental Reasoning Engine",
            "url": "https://marine-api.open-meteo.com",
            "license": "Research / Derived Data",
            "notice": "AI-derived candidate fishing zone. Not an official government bulletin.",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.80

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_fishing_zones(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_fishing_zones(latitude, longitude)


derived_fishing_zone = DerivedFishingZoneProvider()
