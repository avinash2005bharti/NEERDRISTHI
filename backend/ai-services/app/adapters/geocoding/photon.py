"""
Photon Geocoder Fallback (Komoot / OpenStreetMap).
Base URL: https://photon.komoot.io/api/
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
    from app.core.resilience import retry_with_backoff
    from app.schemas.adapters import GeocodedLocation
    from app.core.config import settings
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...core.resilience import retry_with_backoff
    from ...schemas.adapters import GeocodedLocation
    from ...core.config import settings


class PhotonGeocoderProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Photon-OSM",
            category="geocoding",
            base_url="https://photon.komoot.io",
            requires_api_key=False,
            rate_limit_per_second=2.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get("/api/", params={"q": "Mumbai", "limit": 1})
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Optional[GeocodedLocation]:
        # Photon reverse: /reverse?lon=..&lat=..
        await self.rate_limiter.acquire()
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get("/reverse", params={"lon": longitude, "lat": latitude})
                if res.is_success:
                    data = res.json()
                    features = data.get("features", [])
                    if features:
                        return self.normalize_response(features[0])
        except Exception:
            pass
        return None

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    async def search(self, query: str) -> Optional[GeocodedLocation]:
        await self.rate_limiter.acquire()
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get("/api/", params={"q": query, "limit": 1})
                if res.is_success:
                    data = res.json()
                    features = data.get("features", [])
                    if features:
                        return self.normalize_response(features[0])
        except Exception:
            pass
        return None

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> GeocodedLocation:
        props = raw_data.get("properties", {})
        coords = raw_data.get("geometry", {}).get("coordinates", [0.0, 0.0])
        lon, lat = coords[0], coords[1]
        name = props.get("name") or props.get("city") or props.get("country") or "Coastal location"

        return GeocodedLocation(
            name=name,
            latitude=lat,
            longitude=lon,
            confidence=0.8,
            provider=self.name,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Photon by Komoot",
            "url": "https://photon.komoot.io",
            "license": "ODbL (OpenStreetMap)",
            "notice": "Search data powered by OpenStreetMap and Photon/Komoot.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: GeocodedLocation) -> float:
        return response.confidence


photon_geocoder_provider = PhotonGeocoderProvider()
