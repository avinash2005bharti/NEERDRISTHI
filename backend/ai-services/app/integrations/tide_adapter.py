"""
Tide observation adapter for ORCA.
Routes all tidal water-level queries through the centralized MarineDataGateway.
Strictly isolates LangGraph agents from direct external HTTP calls.
"""
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from .base import BaseDataAdapter
from ..schemas.adapters import TideObservation, DataUnavailableResult
from ..config import settings
from ..cache.valkey_client import cache_client, cache_keys
from ..observability.logger import logger
from ..providers.gateway import marine_data_gateway


class TideAdapter(BaseDataAdapter):
    """
    Adapter for tide and water-level information.
    Delegates to MarineDataGateway (Open-Meteo modeled sea level with WorldTides support).
    """

    def __init__(self):
        super().__init__(
            name="MarineDataGateway-Tide",
            base_url="https://marine-api.open-meteo.com",
            api_key="",
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.tide_endpoint = settings.TIDE_ENDPOINT or "/v1/marine"
        self.marine_base_url = settings.OPEN_METEO_MARINE_URL or "https://marine-api.open-meteo.com"
        self.wave_endpoint = settings.WAVE_FORECAST_ENDPOINT or "/v1/marine"

    def is_configured(self) -> bool:
        return bool(self.base_url) and bool(self.tide_endpoint)


    async def health_check(self) -> Dict[str, Any]:
        status = await marine_data_gateway.get_providers_status()
        return {
            "provider": self.name,
            "status": "reachable",
            "tide_status": status.get("worldtides", {}).get("status", "open_meteo_fallback"),
        }

    async def fetch_tide(
        self, latitude: float, longitude: float, station_name: Optional[str] = None
    ) -> Union[TideObservation, DataUnavailableResult]:
        """Fetch tide/water-level via MarineDataGateway."""
        if not self.is_configured():
            return DataUnavailableResult(
                category="tide",
                provider_name=self.name,
                reason="Tide provider endpoint is unconfigured in environment.",
                is_configured=False,
            )

        now_str = datetime.now(timezone.utc).isoformat()

        # Check Valkey cache first
        cache_key = cache_keys.tide(latitude, longitude)
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data"):
            try:
                return TideObservation(**cached["data"])
            except Exception:
                pass

        gateway_tide = await marine_data_gateway.get_tide(latitude, longitude)
        if not gateway_tide.get("available") or not gateway_tide.get("data"):
            return DataUnavailableResult(
                category="tide",
                provider_name=self.name,
                reason="Water level data currently unavailable for these coordinates.",
                is_configured=True,
            )

        td = gateway_tide["data"]
        obs = TideObservation(
            station_name=td.get("station", station_name or f"Grid ({latitude:.2f}°N, {longitude:.2f}°E)"),
            latitude=latitude,
            longitude=longitude,
            observed_at=td.get("timestamp", now_str),
            tide_height_meters=td.get("water_level") or 0.0,
            tide_type=None,
            provider=td.get("provider", "OpenMeteoMarineFallback"),
            source_url=td.get("source_url", "https://marine-api.open-meteo.com/v1/marine"),
            retrieved_at=now_str,
        )

        await cache_client.set(cache_key, obs.model_dump(), settings.VALKEY_TTL_OCEAN_SECONDS)
        return obs

    async def fetch_tide_data(
        self, latitude: float, longitude: float, station_name: Optional[str] = None
    ) -> Union[TideObservation, DataUnavailableResult]:
        """Alias for compatibility with agents calling fetch_tide_data."""
        return await self.fetch_tide(latitude, longitude, station_name)


tide_adapter = TideAdapter()
