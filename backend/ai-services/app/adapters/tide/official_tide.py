"""
Configurable Official Tide Provider.
Used when the user or institution supplies an official tide API endpoint and credentials.
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


class OfficialTideProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Official-Tide-Provider",
            category="tide",
            base_url=settings.TIDE_BASE_URL,
            api_key=settings.TIDE_API_KEY,
            timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            requires_api_key=False,
        )
        self.endpoint = settings.TIDE_ENDPOINT or ""

    def is_configured(self) -> bool:
        return bool(self.base_url and self.endpoint)

    async def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "provider": self.name,
                "status": "unconfigured",
                "message": "TIDE_BASE_URL or TIDE_ENDPOINT not provided in environment.",
            }
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get("/health", timeout=3.0)
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        if not self.is_configured():
            return self.get_error_status("Official tide provider is unconfigured.")

        async def _call():
            client = await self.get_http_client()
            async with client:
                resp = await client.get(self.endpoint, params={"latitude": latitude, "longitude": longitude})
                resp.raise_for_status()
                return resp.json()

        raw_data = await retry_with_backoff(
            _call,
            max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
            circuit_breaker=self.circuit_breaker,
            provider_name=self.name,
        )
        return self.normalize_response(raw_data, latitude=latitude, longitude=longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> TideObservation:
        now_str = datetime.now(timezone.utc).isoformat()
        return TideObservation(
            station=raw_data.get("station_name", "Official Coastal Station"),
            station_id=raw_data.get("station_id", "OFFICIAL-01"),
            observed_or_predicted=raw_data.get("type", "predicted"),
            timestamp=raw_data.get("timestamp", now_str),
            water_level=float(raw_data.get("water_level_m") or raw_data.get("height_meters", 1.5)),
            datum=raw_data.get("datum", "Chart Datum (CD)"),
            units="meters",
            provider=self.name,
            source_url=f"{self.base_url}{self.endpoint}",
            data_status="prediction",
            confidence=0.95,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Official Marine Authority Tide Gauge Network",
            "url": self.base_url or "https://incois.gov.in",
            "license": "Restricted / Authorized Access Only",
            "notice": "Official tide prediction data from configured authority.",
            "type": "restricted_government_api",
            "requires_key": "true",
        }

    def get_data_timestamp(self, response: TideObservation) -> Optional[str]:
        return response.timestamp

    def get_confidence(self, response: TideObservation) -> float:
        return response.confidence


official_tide_provider = OfficialTideProvider()
