"""
Geocoder adapter for ORCA.
Resolves coastal place names and harbor locations to (longitude, latitude) coordinates.
Routes through centralized MarineDataGateway (Nominatim Provider with strict 1 req/s rate-limiting).
Strictly isolates LangGraph agents from direct external HTTP calls.
"""
from typing import Optional, Dict, Any, Union
from .base import BaseDataAdapter
from ..schemas.adapters import GeocodedLocation, DataUnavailableResult
from ..config import settings
from ..cache.valkey_client import cache_client, cache_keys
from ..observability.logger import logger
from ..providers.gateway import marine_data_gateway


class GeocoderAdapter(BaseDataAdapter):
    """
    Adapter for coastal place and harbor geocoding.
    Delegates to MarineDataGateway (Nominatim Provider).
    """

    def __init__(self):
        super().__init__(
            name="CoastalGeocoder",
            base_url=settings.GEOCODER_BASE_URL or "https://nominatim.openstreetmap.org",
            api_key=settings.GEOCODER_API_KEY,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.geocoder_endpoint = settings.GEOCODER_ENDPOINT or "/search"

    def is_configured(self) -> bool:
        return bool(self.base_url and self.geocoder_endpoint)

    async def health_check(self) -> Dict[str, Any]:
        status = await marine_data_gateway.get_providers_status()
        return {
            "provider": self.name,
            "status": "reachable" if status["nominatim"]["status"] == "available" else "degraded",
            "nominatim": status["nominatim"],
        }

    async def resolve_place_name(
        self, place_name: str
    ) -> Union[GeocodedLocation, DataUnavailableResult]:
        """Geocode a place name into WGS84 coordinates via MarineDataGateway."""
        if not self.is_configured():
            return DataUnavailableResult(
                category="geospatial",
                provider_name=self.name,
                reason="Geocoder provider endpoint is unconfigured in environment.",
                is_configured=False,
            )

        if not place_name or not place_name.strip():
            return DataUnavailableResult(
                category="geospatial",
                provider_name=self.name,
                reason="Empty place name provided for geocoding.",
                is_configured=True,
            )

        clean_name = place_name.strip()
        cache_key = cache_keys.geocode(clean_name)
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data"):
            try:
                return GeocodedLocation(**cached["data"])
            except Exception:
                pass

        location = await marine_data_gateway.geocode_location(clean_name)
        if not location:
            return DataUnavailableResult(
                category="geospatial",
                provider_name=self.name,
                reason=f"Place name '{clean_name}' could not be resolved by Nominatim.",
                is_configured=True,
            )

        result = GeocodedLocation(
            name=location.name or clean_name,
            latitude=location.latitude,
            longitude=location.longitude,
            confidence=0.90,
            provider="Nominatim-Gateway",
        )

        await cache_client.set(cache_key, result.model_dump(), settings.VALKEY_TTL_GEOCODE_SECONDS)
        return result


geocoder_adapter = GeocoderAdapter()
