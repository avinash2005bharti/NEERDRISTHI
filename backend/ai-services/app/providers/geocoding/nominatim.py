"""
Nominatim / OpenStreetMap Geocoding Provider for ORCA.
Provides forward geocoding and reverse geocoding with marine/coastal bias.
Rate limit: strictly 1 request/second per OSM public usage policy.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import httpx

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.geocoding.base import BaseGeocoderProvider
    from app.schemas.marine import Location
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff, RateLimiter
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseGeocoderProvider
    from ...schemas.marine import Location
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff, RateLimiter
    from ...observability.logger import logger


class NominatimProvider(BaseGeocoderProvider):
    """
    Nominatim Geocoder Provider.
    Complies with OSM Nominatim usage policy (custom descriptive User-Agent, max 1 req/s).
    """

    USER_AGENT = "ORCA-SIH26176-Hackathon/1.0 (contact: student-team@sih26176.in; marine safety project)"

    def __init__(self):
        super().__init__(
            name="Nominatim",
            category="geocoding",
            base_url=settings.GEOCODER_BASE_URL or "https://nominatim.openstreetmap.org",
            requires_api_key=False,
            rate_limit_per_second=1.0,  # Max 1 req/s per OSM policy
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.search_endpoint = settings.GEOCODER_ENDPOINT or "/search"
        self.reverse_endpoint = "/reverse"
        self._cache: Dict[str, Any] = {}

    async def health_check(self) -> Dict[str, Any]:
        """Check reachability of Nominatim server."""
        try:
            async with self.get_http_client(
                custom_headers={"User-Agent": self.USER_AGENT},
                timeout=5.0,
            ) as client:
                res = await client.get(
                    self.search_endpoint,
                    params={"q": "Goa", "format": "json", "limit": 1},
                )
                return {
                    "provider": self.name,
                    "status": "available" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unavailable", "error": str(e)}

    async def geocode(self, query: str) -> Optional[Location]:
        """Forward geocoding: resolve place name to coordinates."""
        if not query or not query.strip():
            return None

        clean_query = query.strip()
        cache_key = f"geo:{clean_query.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        await self.rate_limiter.acquire()

        async def _call() -> List[Dict[str, Any]]:
            async with self.get_http_client(
                custom_headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout_seconds,
            ) as client:
                params = {
                    "q": clean_query,
                    "format": "json",
                    "limit": 5,
                    "addressdetails": 1,
                    "countrycodes": "in",  # India priority
                }
                res = await client.get(self.search_endpoint, params=params)
                if res.status_code == 429:
                    logger.warning("[Nominatim] Rate limit hit (HTTP 429)")
                    raise httpx.HTTPStatusError("Rate limited", request=res.request, response=res)
                res.raise_for_status()
                data = res.json()
                if not data:
                    # Retry without country restriction
                    res2 = await client.get(
                        self.search_endpoint,
                        params={"q": clean_query, "format": "json", "limit": 1},
                    )
                    if res2.is_success:
                        data = res2.json()
                return data

        try:
            results = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            if not results:
                return None

            best = self._select_best_result(results)
            lat = float(best.get("lat") or 0.0)
            lon = float(best.get("lon") or 0.0)
            loc = Location(
                latitude=lat,
                longitude=lon,
                name=best.get("display_name", clean_query),
            )
            self._cache[cache_key] = loc
            return loc
        except Exception as e:
            logger.warning(f"[{self.name}] Geocode error for '{clean_query}': {e}")
            return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """Reverse geocoding: resolve coordinates to place name."""
        if not self.validate_coordinates(latitude, longitude):
            return None

        cache_key = f"rev:{round(latitude, 3)}:{round(longitude, 3)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        await self.rate_limiter.acquire()

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(
                custom_headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout_seconds,
            ) as client:
                res = await client.get(
                    self.reverse_endpoint,
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "json",
                        "zoom": 12,
                    },
                )
                res.raise_for_status()
                return res.json()

        try:
            res = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            name = res.get("display_name")
            if name:
                self._cache[cache_key] = name
            return name
        except Exception as e:
            logger.warning(f"[{self.name}] Reverse geocode error for ({latitude}, {longitude}): {e}")
            return None

    @staticmethod
    def _select_best_result(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prioritize coastal, harbor, and port features over inland features."""
        coastal_tokens = {"harbour", "port", "pier", "marina", "dock", "quay", "beach", "coast", "fishing"}
        for r in results:
            r_type = str(r.get("type", "")).lower()
            r_class = str(r.get("class", "")).lower()
            if any(t in r_type or t in r_class for t in coastal_tokens):
                return r
        return results[0]

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "OpenStreetMap / Nominatim",
            "url": "https://nominatim.openstreetmap.org",
            "license": "Open Database License (ODbL)",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.95

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.reverse_geocode(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.reverse_geocode(latitude, longitude)


nominatim_provider = NominatimProvider()
