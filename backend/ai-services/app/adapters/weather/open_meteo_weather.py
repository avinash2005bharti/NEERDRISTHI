"""
Open-Meteo Weather API Adapter.
Free, open-data, non-commercial tier requires no API key.
Endpoint: GET /v1/forecast
Variables: temperature_2m, relative_humidity_2m, precipitation, rain, weather_code,
           cloud_cover, surface_pressure, wind_speed_10m, wind_direction_10m,
           wind_gusts_10m, visibility.
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
    from app.schemas.normalized import WeatherForecast
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import WeatherForecast
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class OpenMeteoWeatherProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Open-Meteo Weather API",
            category="weather",
            base_url=settings.WEATHER_BASE_URL or "https://api.open-meteo.com",
            api_key=settings.WEATHER_API_KEY,
            timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            rate_limit_per_second=10.0,
            requires_api_key=False,
        )
        self.endpoint = settings.WEATHER_FORECAST_ENDPOINT or "/v1/forecast"

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get(
                    self.endpoint,
                    params={"latitude": 18.98, "longitude": 72.83, "current": "temperature_2m"},
                )
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> WeatherForecast:
        return await self.fetch_forecast(latitude, longitude, forecast_days=1, **kwargs)

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
        hourly_vars: Optional[List[str]] = None,
        daily_vars: Optional[List[str]] = None,
        timezone_str: str = "auto",
        forecast_model: Optional[str] = None,
        **kwargs
    ) -> WeatherForecast:
        if not self.validate_coordinates(latitude, longitude):
            raise ValueError(f"Invalid coordinates: ({latitude}, {longitude})")

        default_hourly = [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "cloud_cover",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "visibility",
        ]
        hourly = hourly_vars or default_hourly

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(hourly),
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm",
            "forecast_days": min(max(1, forecast_days), 14),
            "timezone": timezone_str,
        }
        if daily_vars:
            params["daily"] = ",".join(daily_vars)
        if forecast_model:
            params["models"] = forecast_model

        async def _call_api():
            client = await self.get_http_client()
            async with client:
                resp = await client.get(self.endpoint, params=params)
                resp.raise_for_status()
                return resp.json()

        raw_data = await retry_with_backoff(
            _call_api,
            max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
            circuit_breaker=self.circuit_breaker,
            provider_name=self.name,
        )

        return self.normalize_response(raw_data, latitude=latitude, longitude=longitude)

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> WeatherForecast:
        lat = kwargs.get("latitude", raw_data.get("latitude", 0.0))
        lon = kwargs.get("longitude", raw_data.get("longitude", 0.0))
        now_str = datetime.now(timezone.utc).isoformat()

        hourly_raw = raw_data.get("hourly", {})
        hourly_units = raw_data.get("hourly_units", {})
        times = hourly_raw.get("time", [])

        valid_from = times[0] if times else now_str
        valid_to = times[-1] if times else now_str

        return WeatherForecast(
            location=f"Coordinates ({lat:.3f}°N, {lon:.3f}°E)",
            latitude=lat,
            longitude=lon,
            timezone=raw_data.get("timezone", "UTC"),
            issued_at=now_str,
            valid_from=valid_from,
            valid_to=valid_to,
            hourly_values=hourly_raw,
            units=hourly_units,
            provider=self.name,
            source_url="https://api.open-meteo.com/v1/forecast",
            data_status="forecast",
            confidence=0.92,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Open-Meteo",
            "url": "https://open-meteo.com",
            "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "notice": "Weather forecast data courtesy of Open-Meteo and national weather services.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: WeatherForecast) -> Optional[str]:
        return response.issued_at

    def get_confidence(self, response: WeatherForecast) -> float:
        return response.confidence


open_meteo_weather_provider = OpenMeteoWeatherProvider()
