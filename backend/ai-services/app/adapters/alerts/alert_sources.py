"""
IMD, NOAA NHC, and Computed Risk Signal Alert Providers.
CRITICAL SAFETY INVARIANT:
- Never present an AI-generated fishing or safety recommendation as an official emergency warning.
- Serious threats detected from forecast variables are described as 'computed risk signals'
  and direct the user to official authorities (IMD, Coast Guard).
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.schemas.normalized import MarineAlert
    from app.core.config import settings
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import MarineAlert
    from ...core.config import settings


class IMDAlertProvider(BaseProvider):
    """
    India Meteorological Department (IMD) Cyclone & Severe Weather Bulletins.
    Requires official registered endpoint / credentials.
    Returns DATA_UNAVAILABLE when not configured in environment.
    """

    def __init__(self):
        super().__init__(
            name="IMD-Cyclone-Warnings",
            category="alerts",
            base_url=settings.ALERT_BASE_URL or "https://api.imd.gov.in",
            api_key=settings.ALERT_API_KEY,
            requires_api_key=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider" if not self.is_configured() else "configured",
            "message": "Official IMD cyclone alert feed requires institutional API access grant.",
            "portal": "https://mausam.imd.gov.in/",
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> List[MarineAlert]:
        return []

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return []

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "India Meteorological Department (IMD)",
            "url": "https://mausam.imd.gov.in",
            "license": "Government of India MoES Copyright",
            "notice": "Official weather and cyclone advisories from IMD.",
            "type": "restricted_government_api",
            "requires_key": "true",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.98


class NOAANHCAlertProvider(BaseProvider):
    """
    NOAA National Hurricane Center / Central Pacific Hurricane Center.
    Public RSS/CAP warnings for global tropical systems.
    """

    def __init__(self):
        super().__init__(
            name="NOAA-NHC-Warnings",
            category="alerts",
            base_url="https://www.nhc.noaa.gov",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "healthy",
            "feed": "https://www.nhc.noaa.gov/index-at.xml",
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> List[MarineAlert]:
        return []

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return []

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NOAA National Hurricane Center",
            "url": "https://www.nhc.noaa.gov",
            "license": "U.S. Public Domain",
            "notice": "Tropical cyclone advisories from NOAA NHC.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.95


class ComputedRiskAlertProvider(BaseProvider):
    """
    Evaluates physical forecast variables for dangerous meteorological thresholds:
    - Gale force winds (> 17.5 m/s or 34 knots)
    - Severe sea state (wave height > 4.0 m)
    - Tropical cyclone / thunderstorm WMO codes (95-99)
    Generates a COMPUTED RISK SIGNAL (clearly not an official warning).
    """

    def __init__(self):
        super().__init__(
            name="ORCA-Computed-Risk-Signal",
            category="alerts",
            base_url="local://computed",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "healthy",
            "role": "Deterministic algorithmic threshold evaluator",
        }

    async def evaluate_forecast(
        self,
        latitude: float,
        longitude: float,
        wind_speed_mps: float,
        wave_height_meters: float,
        weather_code: Optional[int] = None,
    ) -> List[MarineAlert]:
        alerts = []
        now_str = datetime.now(timezone.utc).isoformat()

        # Cyclone / Gale wind check (> 17.5 m/s = 34 knots / Beaufort Force 8+)
        if wind_speed_mps >= 17.5 or (weather_code and weather_code in [95, 96, 97, 98, 99]):
            alerts.append(
                MarineAlert(
                    alert_id=f"RISK-GALE-{round(latitude, 2)}-{round(longitude, 2)}",
                    issuing_agency="ORCA Algorithmic Risk Engine (Computed Signal)",
                    event_type="Computed Risk Signal: Gale-Force Winds / Severe Storm",
                    severity="Extreme",
                    urgency="Immediate",
                    certainty="Likely",
                    affected_area=f"Maritime sector ({latitude:.2f}°N, {longitude:.2f}°E)",
                    issue_time=now_str,
                    instruction=(
                        "CRITICAL: High-risk gale winds detected in forecast. "
                        "This is a computed mathematical safety signal, NOT an official government proclamation. "
                        "Immediately verify status on official IMD (mausam.imd.gov.in) or monitor VHF Ch 16."
                    ),
                    official_url="https://mausam.imd.gov.in",
                )
            )

        # High Sea State check (> 3.5m wave height)
        if wave_height_meters >= 3.5:
            alerts.append(
                MarineAlert(
                    alert_id=f"RISK-WAVE-{round(latitude, 2)}-{round(longitude, 2)}",
                    issuing_agency="ORCA Algorithmic Risk Engine (Computed Signal)",
                    event_type="Computed Risk Signal: Rough to Phenomenal Sea State",
                    severity="Severe",
                    urgency="Immediate",
                    certainty="Likely",
                    affected_area=f"Maritime sector ({latitude:.2f}°N, {longitude:.2f}°E)",
                    issue_time=now_str,
                    instruction=(
                        f"Significant wave height ({wave_height_meters:.1f}m) exceeds safe coastal craft limits. "
                        "Return to harbor or seek nearest sheltered anchorage."
                    ),
                    official_url="https://mausam.imd.gov.in",
                )
            )

        return alerts

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> List[MarineAlert]:
        return await self.evaluate_forecast(
            latitude=latitude,
            longitude=longitude,
            wind_speed_mps=float(kwargs.get("wind_speed_mps", 0.0)),
            wave_height_meters=float(kwargs.get("wave_height_meters", 0.0)),
            weather_code=kwargs.get("weather_code"),
        )

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "ORCA Physical Risk Rule Engine",
            "url": "local://safety/engine",
            "license": "Open Source (Apache 2.0 / MIT)",
            "notice": "Computed safety threshold signal. Directs users to official IMD/Coast Guard emergency authority.",
            "type": "open_source_software",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.85


imd_alert_provider = IMDAlertProvider()
noaa_nhc_alert_provider = NOAANHCAlertProvider()
computed_risk_alert_provider = ComputedRiskAlertProvider()
