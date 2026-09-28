"""
Nominatim / OpenStreetMap Geocoding Adapter.
Supports forward geocoding (/search) and reverse geocoding (/reverse).
Strictly adheres to OSM usage policy:
- Descriptive User-Agent header with application name and contact email
- Rate limiting (max 1 request per second on public instance)
- Local query caching to reduce repeated upstream requests
- Configurable base URL for self-hosted instances
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
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff, RateLimiter
    from app.schemas.adapters import GeocodedLocation
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff, RateLimiter
    from ...schemas.adapters import GeocodedLocation
    from ...observability.logger import logger


class NominatimGeocoderProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Nominatim-OpenStreetMap",
            category="geocoding",
            base_url=settings.GEOCODER_BASE_URL or "https://nominatim.openstreetmap.org",
            api_key=settings.GEOCODER_API_KEY,
            timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            rate_limit_per_second=float(settings.GEOCODER_RATE_LIMIT_PER_SECOND or 1.0),
            requires_api_key=False,
        )
        self.user_agent = settings.GEOCODER_USER_AGENT or "ORCA-SIH26176/1.0 contact@example.com"
        self._cache: Dict[str, GeocodedLocation] = {}

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client(custom_headers={"User-Agent": self.user_agent})
            async with client:
                res = await client.get("/search", params={"q": "Mumbai", "format": "json", "limit": 1})
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Optional[GeocodedLocation]:
        """Reverse geocode coordinates to place name."""
        return await self.reverse_geocode(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    async def search(self, query: str) -> Optional[GeocodedLocation]:
        """Forward geocoding: resolve place name to coordinates."""
        if not query or not query.strip():
            return None

        normalized_q = query.strip().lower()
        if normalized_q in self._cache:
            return self._cache[normalized_q]

        await self.rate_limiter.acquire()

        async def _call_search():
            client = await self.get_http_client(custom_headers={"User-Agent": self.user_agent})
            async with client:
                resp = await client.get(
                    "/search",
                    params={
                        "q": query.strip(),
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                )
                resp.raise_for_status()
                return resp.json()

        results = await retry_with_backoff(
            _call_search,
            max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
            circuit_breaker=self.circuit_breaker,
            provider_name=self.name,
        )

        if not results or not isinstance(results, list):
            return None

        top = results[0]
        loc = self.normalize_response(top)
        self._cache[normalized_q] = loc
        return loc

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeocodedLocation]:
        """Reverse geocoding: coordinates to place name."""
        if not self.validate_coordinates(latitude, longitude):
            return None

        cache_key = f"rev:{round(latitude, 4)}:{round(longitude, 4)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        await self.rate_limiter.acquire()

        async def _call_reverse():
            client = await self.get_http_client(custom_headers={"User-Agent": self.user_agent})
            async with client:
                resp = await client.get(
                    "/reverse",
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "json",
                        "zoom": 12,
                    },
                )
                resp.raise_for_status()
                return resp.json()

        data = await retry_with_backoff(
            _call_reverse,
            max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
            circuit_breaker=self.circuit_breaker,
            provider_name=self.name,
        )

        if not data or "display_name" not in data:
            return None

        loc = self.normalize_response(data)
        self._cache[cache_key] = loc
        return loc

    def normalize_response(self, raw_data: Dict[str, Any], **kwargs) -> GeocodedLocation:
        name = raw_data.get("display_name", "Unknown Coastal Location")
        lat = float(raw_data.get("lat", 0.0))
        lon = float(raw_data.get("lon", 0.0))
        bbox = [float(b) for b in raw_data.get("boundingbox", [])] if raw_data.get("boundingbox") else None

        importance = float(raw_data.get("importance", 0.8))

        return GeocodedLocation(
            name=name,
            latitude=lat,
            longitude=lon,
            confidence=min(1.0, max(0.1, importance)),
            bounding_box=bbox,
            provider=self.name,
        )

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "OpenStreetMap Nominatim",
            "url": "https://nominatim.openstreetmap.org",
            "license": "Open Data Commons Open Database License (ODbL) by OpenStreetMap Foundation",
            "notice": "Geocoding data (c) OpenStreetMap contributors.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: GeocodedLocation) -> float:
        return response.confidence


nominatim_geocoder_provider = NominatimGeocoderProvider()
