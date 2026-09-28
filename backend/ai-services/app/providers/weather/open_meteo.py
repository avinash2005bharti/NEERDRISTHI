"""
Open-Meteo Weather Provider for ORCA.
Primary atmospheric forecast provider (free open data, no API key required).
Endpoint: https://api.open-meteo.com/v1/forecast
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
    from app.providers.weather.base import BaseWeatherProvider
    from app.schemas.marine import WeatherData, DataSource
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseWeatherProvider
    from ...schemas.marine import WeatherData, DataSource
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class OpenMeteoWeatherProvider(BaseWeatherProvider):
    """
    Open-Meteo Atmospheric Weather Provider.
    Primary, non-commercial open data tier.
    """

    def __init__(self):
        super().__init__(
            name="Open-Meteo-Weather",
            category="weather",
            base_url=settings.WEATHER_BASE_URL or "https://api.open-meteo.com",
            api_key=settings.WEATHER_API_KEY,
            requires_api_key=False,
            rate_limit_per_second=10.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.endpoint = settings.WEATHER_FORECAST_ENDPOINT or "/v1/forecast"

    async def health_check(self) -> Dict[str, Any]:
        """Verify reachability of Open-Meteo Weather API."""
        try:
            async with self.get_http_client(timeout=5.0) as client:
                res = await client.get(
                    self.endpoint,
                    params={
                        "latitude": 15.29,
                        "longitude": 73.98,
                        "current": "temperature_2m",
                    },
                )
                res.raise_for_status()
                return {
                    "provider": self.name,
                    "status": "healthy",
                    "code": res.status_code,
                    "latency_ms": res.elapsed.total_seconds() * 1000 if hasattr(res, "elapsed") else 0,
                }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "degraded",
                "error": str(e),
            }

    async def get_weather(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[WeatherData]:
        """Fetch and normalize weather data from Open-Meteo."""
        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                params: Dict[str, Any] = {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "current": [
                        "temperature_2m",
                        "apparent_temperature",
                        "precipitation",
                        "rain",
                        "weather_code",
                        "cloud_cover",
                        "surface_pressure",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "wind_gusts_10m",
                    ],
                    "hourly": [
                        "temperature_2m",
                        "precipitation",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "visibility",
                    ],
                    "wind_speed_unit": "ms",
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
            hourly = data.get("hourly", {})

            # Visibility from current or hourly
            vis = None
            vis_list = hourly.get("visibility", [])
            if vis_list and len(vis_list) > 0 and vis_list[0] is not None:
                vis = float(vis_list[0])

            return WeatherData(
                temperature=current.get("temperature_2m"),
                apparent_temperature=current.get("apparent_temperature"),
                wind_speed=current.get("wind_speed_10m"),
                wind_direction=current.get("wind_direction_10m"),
                wind_gusts=current.get("wind_gusts_10m"),
                precipitation=current.get("precipitation"),
                pressure=current.get("surface_pressure"),
                humidity=None,
                cloud_cover=current.get("cloud_cover"),
                visibility=vis,
                weather_code=current.get("weather_code"),
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to fetch weather for ({latitude}, {longitude}): {e}")
            return None

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_weather(latitude, longitude, date=kwargs.get("date"))


open_meteo_weather = OpenMeteoWeatherProvider()
