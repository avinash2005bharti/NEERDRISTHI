"""
Weather and sea-state data adapter for ORCA.
Routes all meteorological and marine queries through the centralized MarineDataGateway.
Strictly isolates LangGraph agents from direct external HTTP/API calls.
"""
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from .base import BaseDataAdapter
from ..schemas.adapters import WeatherObservation, DataUnavailableResult
from ..config import settings
from ..cache.valkey_client import cache_client, cache_keys
from ..observability.logger import logger
from ..providers.gateway import marine_data_gateway


class WeatherAdapter(BaseDataAdapter):
    """
    Adapter for meteorological and ocean wave forecast.
    Delegates to MarineDataGateway (Open-Meteo Primary with MET Norway fallback).
    """

    def __init__(self):
        super().__init__(
            name="MarineDataGateway-Weather",
            base_url=settings.WEATHER_BASE_URL or "https://api.open-meteo.com",
            api_key=settings.WEATHER_API_KEY,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.forecast_endpoint = settings.WEATHER_FORECAST_ENDPOINT or "/v1/forecast"

    def is_configured(self) -> bool:
        return bool(self.base_url and self.forecast_endpoint)

    async def health_check(self) -> Dict[str, Any]:
        status = await marine_data_gateway.get_providers_status()
        return {
            "provider": self.name,
            "status": "reachable" if status["open_meteo"]["status"] == "available" else "degraded",
            "open_meteo": status["open_meteo"],
            "met_no": status["met_no"],
        }

    async def fetch_weather_and_waves(
        self, latitude: float, longitude: float
    ) -> Union[WeatherObservation, DataUnavailableResult]:
        """
        Fetch weather + sea-state via MarineDataGateway.
        Checks cache, engages fallback if primary fails, and normalizes into WeatherObservation.
        """
        if not self.is_configured():
            return DataUnavailableResult(
                category="weather",
                provider_name=self.name,
                reason="Weather provider endpoint is unconfigured in environment.",
                is_configured=False,
            )

        now_str = datetime.now(timezone.utc).isoformat()

        # Check Valkey cache first
        cache_key = cache_keys.weather(latitude, longitude)
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data"):
            try:
                obs = WeatherObservation(**cached["data"])
                obs_dict = obs.model_dump()
                obs_dict["from_cache"] = True
                return WeatherObservation(**obs_dict)
            except Exception:
                pass

        # Query centralized gateway (orchestrating Open-Meteo, MET Norway, and marine models)
        wx_resp = await marine_data_gateway.get_weather_forecast(latitude, longitude)
        mar_resp = await marine_data_gateway.get_marine_conditions(latitude, longitude)

        wx_avail = wx_resp.get("available", False)
        mar_avail = mar_resp.get("available", False)

        if not wx_avail and not mar_avail:
            return DataUnavailableResult(
                category="weather",
                provider_name=self.name,
                reason="Atmospheric and marine weather services are currently unreachable.",
                is_configured=True,
            )

        wx_data = wx_resp.get("data", {})
        mar_data = mar_resp.get("data", {})

        wind_speed_mps = float(wx_data.get("wind_speed") or 0.0)
        wind_gust_mps = float(wx_data["wind_gusts"]) if wx_data.get("wind_gusts") is not None else None
        wind_direction_deg = float(wx_data["wind_direction"]) if wx_data.get("wind_direction") is not None else None
        precipitation_mm = float(wx_data.get("precipitation") or 0.0)
        weather_code = wx_data.get("weather_code")
        warning_flag = self._wmo_to_warning(int(weather_code)) if weather_code is not None else None

        wave_height_m = float(mar_data.get("wave_height") or 0.0)
        wave_period_s = float(mar_data["wave_period"]) if mar_data.get("wave_period") is not None else None
        swell_height_m = float(mar_data["swell_wave_height"]) if mar_data.get("swell_wave_height") is not None else None
        sea_surface_temp = float(mar_data["sea_surface_temperature"]) if mar_data.get("sea_surface_temperature") is not None else None

        # Build provider attribution string
        active_providers = []
        if wx_avail and wx_resp.get("sources"):
            active_providers.append(wx_resp["sources"][0]["provider"])
        if mar_avail and mar_resp.get("sources"):
            active_providers.append(mar_resp["sources"][0]["provider"])
        provider_name = ", ".join(active_providers) if active_providers else "MarineDataGateway"

        observation = WeatherObservation(
            latitude=latitude,
            longitude=longitude,
            observed_at=now_str,
            valid_until=None,
            wind_speed_mps=wind_speed_mps,
            wind_gust_mps=wind_gust_mps,
            wind_direction_degrees=wind_direction_deg,
            wave_height_meters=wave_height_m,
            wave_period_seconds=wave_period_s,
            swell_height_meters=swell_height_m,
            precipitation_mm=precipitation_mm,
            sea_surface_temp_celsius=sea_surface_temp,
            warning_flag=warning_flag,
            provider=provider_name,
            source_url="https://api.open-meteo.com / https://marine-api.open-meteo.com",
            retrieved_at=now_str,
        )

        if wind_speed_mps > 0 or wave_height_m > 0:
            await cache_client.set(
                cache_key,
                observation.model_dump(),
                ttl_seconds=settings.VALKEY_TTL_WEATHER_SECONDS,
            )

        return observation

    @staticmethod
    def _wmo_to_warning(wmo_code: int) -> Optional[str]:
        """Convert WMO weather interpretation code to warning flag."""
        if wmo_code in range(45, 50):
            return "FOG WARNING"
        elif wmo_code in range(51, 68):
            return "RAIN WARNING"
        elif wmo_code in range(71, 78):
            return "SNOWFALL WARNING"
        elif wmo_code in range(80, 83):
            return "SHOWERS WARNING"
        elif wmo_code in range(85, 87):
            return "SNOW SHOWERS WARNING"
        elif wmo_code in range(95, 100):
            return "THUNDERSTORM WARNING"
        return None


weather_adapter = WeatherAdapter()
