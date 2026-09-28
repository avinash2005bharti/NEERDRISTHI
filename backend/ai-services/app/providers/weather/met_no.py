"""
MET Norway Weather Fallback Provider for ORCA.
Provides secondary high-reliability meteorological data from the Norwegian Meteorological Institute.
Endpoint: https://api.met.no/weatherapi/locationforecast/2.0/complete
Strict TOS Requirement: Must identify application via unique User-Agent.
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
    from app.schemas.marine import WeatherData
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseWeatherProvider
    from ...schemas.marine import WeatherData
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class MetNorwayWeatherProvider(BaseWeatherProvider):
    """
    MET Norway Locationforecast Provider.
    Primary fallback when Open-Meteo is unavailable or rate-limited.
    """

    def __init__(self):
        super().__init__(
            name="MET-Norway",
            category="weather",
            base_url=settings.MET_NO_BASE_URL or "https://api.met.no",
            requires_api_key=False,
            rate_limit_per_second=5.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.endpoint = settings.MET_NO_ENDPOINT or "/weatherapi/locationforecast/2.0/complete"
        self.user_agent = settings.MET_NO_USER_AGENT or "ORCA-SIH26176-Hackathon/1.0 (contact: student-team@sih26176.in)"

    async def health_check(self) -> Dict[str, Any]:
        """Verify reachability of MET Norway API with required User-Agent."""
        try:
            headers = {"User-Agent": self.user_agent}
            async with self.get_http_client(timeout=5.0, custom_headers=headers) as client:
                res = await client.get(
                    self.endpoint,
                    params={"lat": 15.29, "lon": 73.98},
                )
                res.raise_for_status()
                return {
                    "provider": self.name,
                    "status": "healthy" if res.status_code == 200 else "degraded",
                    "code": res.status_code,
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
        """Fetch and normalize weather data from MET Norway."""
        if not settings.MET_NO_ENABLED:
            return None

        async def _call() -> Dict[str, Any]:
            headers = {"User-Agent": self.user_agent}
            async with self.get_http_client(timeout=self.timeout_seconds, custom_headers=headers) as client:
                resp = await client.get(
                    self.endpoint,
                    params={
                        "lat": round(latitude, 4),
                        "lon": round(longitude, 4),
                    },
                )
                resp.raise_for_status()
                return resp.json()

        try:
            data = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            timeseries = data.get("properties", {}).get("timeseries", [])
            if not timeseries:
                return None

            first_point = timeseries[0]
            instant_details = first_point.get("data", {}).get("instant", {}).get("details", {})
            next_1h = first_point.get("data", {}).get("next_1_hours", {}).get("details", {})
            precip = next_1h.get("precipitation_amount")

            return WeatherData(
                temperature=instant_details.get("air_temperature"),
                apparent_temperature=instant_details.get("apparent_air_temperature"),
                wind_speed=instant_details.get("wind_speed"),
                wind_direction=instant_details.get("wind_from_direction"),
                wind_gusts=instant_details.get("wind_speed_of_gust"),
                precipitation=precip if precip is not None else 0.0,
                pressure=instant_details.get("air_pressure_at_sea_level"),
                humidity=instant_details.get("relative_humidity"),
                cloud_cover=instant_details.get("cloud_area_fraction"),
                visibility=None,
                weather_code=None,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to fetch weather for ({latitude}, {longitude}): {e}")
            return None

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_weather(latitude, longitude, date=kwargs.get("date"))


met_norway_weather = MetNorwayWeatherProvider()
