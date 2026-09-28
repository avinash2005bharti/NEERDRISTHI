"""
Open-Meteo Marine Tide & Water-Level Provider for ORCA.
Provides modeled sea-level height relative to Mean Sea Level (MSL).
Endpoint: https://marine-api.open-meteo.com/v1/marine
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.tide.base import BaseTideProvider
    from app.schemas.marine import TideData
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseTideProvider
    from ...schemas.marine import TideData
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class OpenMeteoTideProvider(BaseTideProvider):
    """
    Open-Meteo Marine Water-Level / Sea-Level Provider.
    Extracts sea_level / sea_level_height_msl from numerical ocean model predictions.
    Explicitly tags data as modeled ocean sea level rather than official hydrographic tide tables.
    """

    def __init__(self):
        super().__init__(
            name="Open-Meteo-Tide",
            category="tide",
            base_url=settings.MARINE_BASE_URL or "https://marine-api.open-meteo.com",
            requires_api_key=False,
            rate_limit_per_second=10.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.endpoint = settings.MARINE_FORECAST_ENDPOINT or "/v1/marine"

    async def health_check(self) -> Dict[str, Any]:
        """Check reachability of Open-Meteo marine water-level endpoint."""
        try:
            async with self.get_http_client(timeout=5.0) as client:
                res = await client.get(
                    self.endpoint,
                    params={
                        "latitude": 15.29,
                        "longitude": 73.98,
                        "hourly": "sea_level",
                    },
                )
                return {
                    "provider": self.name,
                    "status": "available" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unavailable", "error": str(e)}

    async def get_tide(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[TideData]:
        """Fetch sea-level height for the given coordinates."""
        if not self.validate_coordinates(latitude, longitude):
            return None

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    self.endpoint,
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "hourly": "sea_level",
                        "timezone": "UTC",
                    },
                )
                resp.raise_for_status()
                return resp.json()

        try:
            raw = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            return self.normalize_response(raw, latitude=latitude, longitude=longitude)
        except Exception as e:
            logger.warning(f"[{self.name}] Failed fetching sea-level for ({latitude}, {longitude}): {e}")
            return None

    def normalize_response(self, raw_data: Any, **kwargs) -> Optional[TideData]:
        if not isinstance(raw_data, dict):
            return None

        hourly = raw_data.get("hourly", {})
        times: List[str] = hourly.get("time", [])
        levels: List[Optional[float]] = hourly.get("sea_level", [])

        if not times or not levels:
            return None

        # Pick nearest hourly value
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        target_idx = 0
        for i, t in enumerate(times):
            if t >= now_utc:
                target_idx = i
                break

        val = levels[target_idx] if target_idx < len(levels) else levels[0]
        timestamp = times[target_idx] if target_idx < len(times) else times[0]

        lat = kwargs.get("latitude", 0.0)
        lon = kwargs.get("longitude", 0.0)

        return TideData(
            station=f"Open-Ocean Grid ({round(lat, 2)}N, {round(lon, 2)}E)",
            station_id=f"grid-{round(lat, 2)}-{round(lon, 2)}",
            water_level=val,
            datum="Mean Sea Level (MSL)",
            timestamp=timestamp,
            provider="Open-Meteo Marine (Modeled Sea Level)",
            data_status="estimated",
            source_url="https://marine-api.open-meteo.com",
            is_official_tide_table=False,
            metadata={
                "notice": "Modeled open-ocean sea-level height above MSL. Not an official hydrographic harmonic tide table.",
                "model": "ECMWF / DWD ocean model",
            },
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Open-Meteo Marine API",
            "url": "https://marine-api.open-meteo.com",
            "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "notice": "Modeled open-ocean sea-level height. Not an official nautical tide table.",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return getattr(response, "timestamp", datetime.now(timezone.utc).isoformat())

    def get_confidence(self, response: Any) -> float:
        return 0.85

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_tide(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_tide(latitude, longitude)


open_meteo_tide = OpenMeteoTideProvider()
