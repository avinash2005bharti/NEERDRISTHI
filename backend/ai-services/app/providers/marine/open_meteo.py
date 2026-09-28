"""
Open-Meteo Marine Provider for ORCA.
Primary sea-state and ocean physical parameters provider.
Endpoint: https://marine-api.open-meteo.com/v1/marine
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.marine.base import BaseMarineProvider
    from app.schemas.marine import MarineData
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseMarineProvider
    from ...schemas.marine import MarineData
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class OpenMeteoMarineProvider(BaseMarineProvider):
    """
    Open-Meteo Marine API Provider.
    Primary ocean waves, swell, SST, and currents provider.
    """

    def __init__(self):
        super().__init__(
            name="Open-Meteo-Marine",
            category="marine",
            base_url=settings.MARINE_BASE_URL or "https://marine-api.open-meteo.com",
            api_key=settings.MARINE_API_KEY,
            requires_api_key=False,
            rate_limit_per_second=10.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.endpoint = settings.MARINE_FORECAST_ENDPOINT or "/v1/marine"

    async def health_check(self) -> Dict[str, Any]:
        """Verify reachability of Open-Meteo Marine API."""
        try:
            async with self.get_http_client(timeout=5.0) as client:
                res = await client.get(
                    self.endpoint,
                    params={
                        "latitude": 15.29,
                        "longitude": 73.98,
                        "current": "wave_height",
                    },
                )
                res.raise_for_status()
                return {
                    "provider": self.name,
                    "status": "healthy",
                    "code": res.status_code,
                }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "degraded",
                "error": str(e),
            }

    async def get_marine(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[MarineData]:
        """Fetch and normalize marine variables from Open-Meteo Marine API."""
        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                params: Dict[str, Any] = {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "current": [
                        "wave_height",
                        "wave_direction",
                        "wave_period",
                        "swell_wave_height",
                        "swell_wave_direction",
                        "sea_surface_temperature",
                        "ocean_current_velocity",
                        "ocean_current_direction",
                        "sea_level_height_msl",
                    ],
                    "timezone": "auto",
                    "forecast_days": 2,
                }
                if date:
                    params["start_date"] = date
                    params["end_date"] = date

                resp = await client.get(self.endpoint, params=params)
                resp.raise_for_status()
                return resp.json()

        try:
            data = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            current = data.get("current", {})

            # Gracefully handle missing variables (some models only return wave data)
            wave_h = current.get("wave_height")
            wave_d = current.get("wave_direction")
            wave_p = current.get("wave_period")
            swell_h = current.get("swell_wave_height")
            swell_d = current.get("swell_wave_direction")
            sst = current.get("sea_surface_temperature")
            curr_v = current.get("ocean_current_velocity")
            curr_d = current.get("ocean_current_direction")
            sea_lvl = current.get("sea_level_height_msl")

            return MarineData(
                wave_height=wave_h,
                wave_direction=wave_d,
                wave_period=wave_p,
                swell_wave_height=swell_h,
                swell_wave_direction=swell_d,
                sea_surface_temperature=sst,
                ocean_current_velocity=curr_v,
                ocean_current_direction=curr_d,
                sea_level=sea_lvl,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to fetch marine data for ({latitude}, {longitude}): {e}")
            return None

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_marine(latitude, longitude, date=kwargs.get("date"))


open_meteo_marine = OpenMeteoMarineProvider()
