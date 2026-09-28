"""
Clearly Labelled Fallback Provider based on Nearby Ocean Water-Level Information.
IMPORTANT NOTICE:
- Does NOT claim to be an official tide prediction.
- Clearly flags observed_or_predicted="estimated".
- Does NOT silently substitute wave height for tide height.
- If sea_level is unavailable, explicitly returns DATA_UNAVAILABLE.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.schemas.normalized import TideObservation
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import TideObservation
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff


class WaterLevelFallbackProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Ocean-Water-Level-Proxy",
            category="tide",
            base_url=settings.MARINE_BASE_URL or "https://marine-api.open-meteo.com",
            requires_api_key=False,
        )
        self.endpoint = settings.MARINE_FORECAST_ENDPOINT or "/v1/marine"

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get(
                    self.endpoint,
                    params={"latitude": 18.98, "longitude": 72.83, "hourly": "sea_level"},
                )
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        if not self.validate_coordinates(latitude, longitude):
            return self.get_error_status("Invalid coordinates.")

        async def _call():
            client = await self.get_http_client()
            async with client:
                resp = await client.get(
                    self.endpoint,
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "hourly": "sea_level",
                        "forecast_days": 1,
                        "timezone": "auto",
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
            hourly = data.get("hourly", {})
            sea_levels = hourly.get("sea_level", [])
            times = hourly.get("time", [])

            # Extract first valid non-null sea level
            val = None
            ts = datetime.now(timezone.utc).isoformat()
            for i, sl in enumerate(sea_levels):
                if sl is not None:
                    val = float(sl)
                    if i < len(times):
                        ts = times[i]
                    break

            if val is None:
                return {
                    "status": "DATA_UNAVAILABLE",
                    "category": "tide",
                    "provider": self.name,
                    "reason": "No configured tide provider for this location (sea_level telemetry returned null).",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            return TideObservation(
                station=f"Water-Level Model Cell ({latitude:.2f}°N, {longitude:.2f}°E)",
                station_id="WL-PROXY-EST",
                observed_or_predicted="estimated",
                timestamp=ts,
                water_level=val,
                datum="Sea Level Anomaly (Non-Harmonic Estimate)",
                units="meters",
                provider=self.name,
                source_url="https://marine-api.open-meteo.com/v1/marine",
                data_status="estimated",
                confidence=0.55,
            )
        except Exception as e:
            return {
                "status": "DATA_UNAVAILABLE",
                "category": "tide",
                "provider": self.name,
                "reason": f"No configured tide provider for this location (Fallback error: {e}).",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Open-Meteo Marine sea_level",
            "url": "https://marine-api.open-meteo.com",
            "license": "CC BY 4.0",
            "notice": "Estimated ocean surface water-level anomaly. NOT an official tide gauge prediction.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: TideObservation) -> Optional[str]:
        return response.timestamp

    def get_confidence(self, response: TideObservation) -> float:
        return response.confidence


water_level_fallback_provider = WaterLevelFallbackProvider()
