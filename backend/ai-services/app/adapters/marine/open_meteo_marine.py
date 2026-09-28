"""
Open-Meteo Marine API Adapter.
Specialized marine endpoint for significant wave height, wave direction,
wave period, swell waves, ocean currents, and sea level.
Base URL: https://marine-api.open-meteo.com
Endpoint: GET /v1/marine
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import httpx

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.schemas.normalized import MarineForecast
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import MarineForecast
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class OpenMeteoMarineProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Open-Meteo Marine API",
            category="marine",
            base_url=settings.MARINE_BASE_URL or "https://marine-api.open-meteo.com",
            api_key=settings.MARINE_API_KEY,
            timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            rate_limit_per_second=10.0,
            requires_api_key=False,
        )
        self.endpoint = settings.MARINE_FORECAST_ENDPOINT or "/v1/marine"

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get(
                    self.endpoint,
                    params={"latitude": 18.98, "longitude": 72.83, "current": "wave_height"},
                )
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> MarineForecast:
        return await self.fetch_forecast(latitude, longitude, forecast_days=1, **kwargs)

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
        **kwargs
    ) -> MarineForecast:
        if not self.validate_coordinates(latitude, longitude):
            raise ValueError(f"Invalid coordinates: ({latitude}, {longitude})")

        marine_current_vars = [
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "wind_wave_direction",
            "wind_wave_period",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period",
        ]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(marine_current_vars),
            "hourly": "wave_height,wave_period",
            "forecast_days": min(max(1, forecast_days), 8),
            "timezone": "auto",
        }

        async def _call_marine():
            client = await self.get_http_client()
            async with client:
                resp = await client.get(self.endpoint, params=params)
                resp.raise_for_status()
                return resp.json()

        raw_data = await retry_with_backoff(
            _call_marine,
            max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
            circuit_breaker=self.circuit_breaker,
            provider_name=self.name,
        )

        return self.normalize_response(raw_data, latitude=latitude, longitude=longitude)

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> MarineForecast:
        lat = kwargs.get("latitude", raw_data.get("latitude", 0.0))
        lon = kwargs.get("longitude", raw_data.get("longitude", 0.0))
        now_str = datetime.now(timezone.utc).isoformat()

        cur = raw_data.get("current", {})
        hourly = raw_data.get("hourly", {})
        units = raw_data.get("current_units", {})
        times = hourly.get("time", [])

        valid_from = times[0] if times else now_str
        valid_to = times[-1] if times else now_str

        # Wind speed estimate if present or derived
        wave_height = float(cur.get("wave_height") or 0.0)
        wave_period = float(cur["wave_period"]) if cur.get("wave_period") is not None else None
        wave_dir = float(cur["wave_direction"]) if cur.get("wave_direction") is not None else None

        current_speed = float(cur["ocean_current_velocity"]) if cur.get("ocean_current_velocity") is not None else None
        current_dir = float(cur["ocean_current_direction"]) if cur.get("ocean_current_direction") is not None else None

        # sea_level from hourly first element
        sea_levels = hourly.get("sea_level", [])
        sea_level = float(sea_levels[0]) if sea_levels and sea_levels[0] is not None else None

        # Swell & wind-wave components
        wind_wave_height = cur.get("wind_wave_height")
        wind_speed_approx = round(float(wind_wave_height) * 4.5, 2) if wind_wave_height is not None else 0.0

        return MarineForecast(
            location=f"Offshore ({lat:.3f}°N, {lon:.3f}°E)",
            latitude=lat,
            longitude=lon,
            issued_at=now_str,
            valid_from=valid_from,
            valid_to=valid_to,
            wave_height=wave_height,
            wave_period=wave_period,
            wave_direction=wave_dir,
            wind_speed=wind_speed_approx,
            wind_direction=cur.get("wind_wave_direction"),
            current_speed=current_speed,
            current_direction=current_dir,
            sea_level=sea_level,
            units={
                "wave_height": "m",
                "wave_period": "s",
                "wind_speed": "m/s",
                "current_speed": "m/s",
                "sea_level": "m",
            },
            provider=self.name,
            source_url="https://marine-api.open-meteo.com/v1/marine",
            data_status="forecast",
            confidence=0.88,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Open-Meteo Marine API",
            "url": "https://open-meteo.com/en/docs/marine-weather-api",
            "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "notice": "Marine wave, current, and sea-level data derived from ECMWF WAM, NOAA WaveWatch III, and DWD models.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: MarineForecast) -> Optional[str]:
        return response.issued_at

    def get_confidence(self, response: MarineForecast) -> float:
        return response.confidence


open_meteo_marine_provider = OpenMeteoMarineProvider()
