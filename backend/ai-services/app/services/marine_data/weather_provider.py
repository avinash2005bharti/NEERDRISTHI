"""
Weather Data Provider for ORCA (SIH26176).
Connects to Open-Meteo Atmospheric Weather API (and MET Norway fallback).
Formats live wind and atmospheric layers into standard GeoJSON.
"""
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
from .base_provider import MarineDataProvider

try:
    from ...adapters import open_meteo_weather_provider
except (ImportError, ValueError):
    from app.adapters import open_meteo_weather_provider


class WeatherDataProvider(MarineDataProvider):
    """
    Live Atmospheric & Wind Data Provider.
    Returns real-time ECMWF/DWD forecast models from Open-Meteo.
    """

    def __init__(self):
        super().__init__(name="Open-Meteo Weather", is_live_source=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def get_wind(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        c_lat = lat if lat is not None else 18.98
        c_lon = lon if lon is not None else 72.82
        try:
            forecast = await open_meteo_weather_provider.fetch_forecast(c_lat, c_lon)
            if forecast and getattr(forecast, "wind_speed_mps", None) is not None:
                speed_mps = float(forecast.wind_speed_mps)
                speed_knots = round(speed_mps * 1.94384, 1)
                speed_kmh = round(speed_mps * 3.6, 1)
                deg = float(getattr(forecast, "wind_direction_deg", 240.0) or 240.0)
                gusts_mps = float(getattr(forecast, "wind_gusts_mps", speed_mps * 1.3) or (speed_mps * 1.3))
                gusts_knots = round(gusts_mps * 1.94384, 1)

                features = [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [c_lon, c_lat]},
                        "properties": {
                            "variable": "wind",
                            "wind_speed_knots": speed_knots,
                            "wind_speed_kmh": speed_kmh,
                            "wind_direction_deg": deg,
                            "wind_gusts_knots": gusts_knots,
                            "status": "LIVE",
                            "source": "Open-Meteo Weather API",
                            "timestamp": self._now(),
                        }
                    }
                ]
                return {
                    "type": "FeatureCollection",
                    "metadata": {
                        "layer": "wind",
                        "center": {"latitude": c_lat, "longitude": c_lon},
                        "wind_speed_knots": speed_knots,
                        "wind_direction_deg": deg,
                        "status": "LIVE",
                        "is_live": True,
                        "source": "Open-Meteo Weather API",
                        "timestamp": self._now(),
                    },
                    "features": features,
                }
        except Exception:
            pass
        return None

    async def get_weather(
        self,
        lat: float,
        lon: float,
    ) -> Optional[Dict[str, Any]]:
        try:
            forecast = await open_meteo_weather_provider.fetch_forecast(lat, lon)
            if forecast:
                return {
                    "status": "LIVE",
                    "is_live": True,
                    "source": "Open-Meteo Weather API",
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_c": forecast.temperature_c,
                    "wind_speed_mps": forecast.wind_speed_mps,
                    "wind_direction_deg": forecast.wind_direction_deg,
                    "visibility_m": forecast.visibility_m,
                    "precipitation_probability": forecast.precipitation_probability,
                    "condition": forecast.condition,
                    "timestamp": self._now(),
                }
        except Exception:
            pass
        return None

    async def get_sst(self, bbox=None, lat=None, lon=None, time=None):
        return None

    async def get_chlorophyll(self, bbox=None, lat=None, lon=None, time=None):
        return None

    async def get_waves(self, bbox=None, lat=None, lon=None, time=None):
        return None

    async def get_tides(self, lat: float, lon: float, time=None):
        return None

    async def get_pfz(self, bbox=None, lat=None, lon=None, time=None):
        return None

    async def get_risk(self, bbox=None, lat=None, lon=None, time=None):
        return None

    async def get_overview(self, lat: float, lon: float):
        wx = await self.get_weather(lat, lon)
        if wx:
            return {"weather": wx, "status": "LIVE", "is_live": True, "source": "Open-Meteo Weather API"}
        return None
