"""
WorldTides Provider for ORCA.
Optional harmonic tide predictions provider.
Requires WORLDTIDES_ENABLED=true and WORLDTIDES_API_KEY.
If unconfigured or disabled, gracefully degrades so Open-Meteo is used as primary fallback.
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


class WorldTidesProvider(BaseTideProvider):
    """
    WorldTides API Provider.
    Optional global tidal prediction provider.
    """

    def __init__(self):
        super().__init__(
            name="WorldTides",
            category="tide",
            base_url="https://www.worldtides.info/api/v3",
            api_key=settings.WORLDTIDES_API_KEY,
            requires_api_key=True,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )

    def is_configured(self) -> bool:
        return bool(settings.WORLDTIDES_ENABLED and settings.WORLDTIDES_API_KEY)

    async def health_check(self) -> Dict[str, Any]:
        """Check status of WorldTides provider."""
        if not settings.WORLDTIDES_ENABLED:
            return {
                "provider": self.name,
                "status": "disabled",
                "message": "WorldTides is disabled (WORLDTIDES_ENABLED=false)",
            }
        if not self.is_configured():
            return {
                "provider": self.name,
                "status": "credentials_missing",
                "message": "WORLDTIDES_API_KEY not configured.",
            }
        return {
            "provider": self.name,
            "status": "available",
            "message": "WorldTides API key is configured.",
        }

    async def get_tide(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[TideData]:
        """Fetch tide height from WorldTides API if enabled and configured."""
        if not self.is_configured():
            return None

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    self.base_url,
                    params={
                        "heights": "",
                        "lat": latitude,
                        "lon": longitude,
                        "key": self.api_key,
                        "days": 1,
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
            logger.warning(f"[{self.name}] Failed fetching tide data: {e}")
            return None

    def normalize_response(self, raw_data: Any, **kwargs) -> Optional[TideData]:
        if not isinstance(raw_data, dict):
            return None

        heights = raw_data.get("heights", [])
        if not heights:
            return None

        latest = heights[0]
        station = raw_data.get("station", "WorldTides Station")
        lat = kwargs.get("latitude", 0.0)
        lon = kwargs.get("longitude", 0.0)

        return TideData(
            station=station,
            station_id=f"wt-{round(lat, 2)}-{round(lon, 2)}",
            water_level=float(latest.get("height", 0.0)),
            datum=raw_data.get("datum", "LAT"),
            timestamp=latest.get("date", datetime.now(timezone.utc).isoformat()),
            provider="WorldTides",
            data_status="prediction",
            source_url="https://www.worldtides.info",
            is_official_tide_table=False,
            metadata={"source": "WorldTides global model"},
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "WorldTides",
            "url": "https://www.worldtides.info",
            "license": "Commercial / Registered Open API",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return getattr(response, "timestamp", datetime.now(timezone.utc).isoformat())

    def get_confidence(self, response: Any) -> float:
        return 0.90

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_tide(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_tide(latitude, longitude)


worldtides_provider = WorldTidesProvider()
