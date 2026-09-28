"""
NOAA CO-OPS Tides and Currents API Adapter.
Public REST API provided by NOAA Center for Operational Oceanographic Products and Services.
URL: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
Free, open data, no API key required.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

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


class NOAACOOPSTideProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="NOAA-CO-OPS-Tides",
            category="tide",
            base_url="https://api.tidesandcurrents.noaa.gov",
            requires_api_key=False,
        )
        self.endpoint = "/api/prod/datagetter"

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                # Query verified station 9414290 (San Francisco)
                res = await client.get(
                    self.endpoint,
                    params={
                        "date": "today",
                        "station": "9414290",
                        "product": "predictions",
                        "datum": "MLLW",
                        "time_zone": "gmt",
                        "units": "metric",
                        "format": "json",
                    },
                )
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, station_id: Optional[str] = None, **kwargs) -> Any:
        station = station_id or settings.TIDE_STATION_ID
        if not station:
            # If coordinates are outside US/territories coverage and no station given, return unavailable
            return self.get_error_status("NOAA CO-OPS requires a supported station ID for coastal regions outside US.")

        async def _call():
            client = await self.get_http_client()
            async with client:
                res = await client.get(
                    self.endpoint,
                    params={
                        "date": "today",
                        "station": station,
                        "product": "predictions",
                        "datum": "MLLW",
                        "time_zone": "gmt",
                        "units": "metric",
                        "format": "json",
                    },
                )
                res.raise_for_status()
                return res.json()

        try:
            raw = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            return self.normalize_response(raw, latitude=latitude, longitude=longitude, station_id=station)
        except Exception as e:
            return self.get_error_status(f"NOAA CO-OPS query failed: {e}")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> TideObservation:
        predictions = raw_data.get("predictions", [])
        now_str = datetime.now(timezone.utc).isoformat()
        level = float(predictions[0].get("v", 0.0)) if predictions else 0.0
        pred_time = predictions[0].get("t", now_str) if predictions else now_str

        return TideObservation(
            station=f"NOAA Station {kwargs.get('station_id')}",
            station_id=kwargs.get("station_id", "NOAA"),
            observed_or_predicted="predicted",
            timestamp=pred_time,
            water_level=level,
            datum="Mean Lower Low Water (MLLW)",
            units="meters",
            provider=self.name,
            source_url="https://tidesandcurrents.noaa.gov",
            data_status="prediction",
            confidence=0.92,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NOAA CO-OPS",
            "url": "https://tidesandcurrents.noaa.gov",
            "license": "U.S. Public Domain",
            "notice": "Tide predictions from NOAA Center for Operational Oceanographic Products and Services.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: TideObservation) -> Optional[str]:
        return response.timestamp

    def get_confidence(self, response: TideObservation) -> float:
        return response.confidence


noaa_coops_tide_provider = NOAACOOPSTideProvider()
