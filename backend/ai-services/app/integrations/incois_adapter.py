"""
INCOIS and Marine Fishing Zone Adapter for ORCA.
Routes all PFZ and oceanographic productivity queries through the centralized MarineDataGateway.
Strictly isolates LangGraph agents from direct external HTTP calls.
Distinguishes between official INCOIS bulletins and AI-derived candidate fishing zones.
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from .base import BaseDataAdapter
from ..schemas.adapters import PFZRecord, DataUnavailableResult
from ..schemas.geojson import PointGeometry
from ..config import settings
from ..cache.valkey_client import cache_client, cache_keys
from ..observability.logger import logger
from ..providers.gateway import marine_data_gateway


class INCOISAdapter(BaseDataAdapter):
    """
    Adapter for Potential Fishing Zone (PFZ) data.
    Delegates to MarineDataGateway (Official INCOIS PFZ when configured, otherwise AI-derived candidate zones).
    """

    def __init__(self):
        super().__init__(
            name="MarineDataGateway-PFZ",
            base_url=settings.INCOIS_BASE_URL or "https://erddap.incois.gov.in/erddap",
            api_key=settings.INCOIS_API_KEY,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.pfz_endpoint = settings.INCOIS_PFZ_ENDPOINT or "/pfz"

    def is_configured(self) -> bool:
        return bool(self.base_url and self.pfz_endpoint)

    async def health_check(self) -> Dict[str, Any]:
        status = await marine_data_gateway.get_providers_status()
        return {
            "provider": self.name,
            "status": "reachable",
            "incois_erddap": status.get("incois_erddap"),
            "incois_official": status.get("incois_official_pfz"),
        }

    async def fetch_pfz(
        self, latitude: float, longitude: float
    ) -> Union[List[PFZRecord], DataUnavailableResult]:
        """
        Fetch PFZ records via MarineDataGateway.
        Uses official INCOIS PFZ if institutional credentials configured;
        otherwise returns clearly-labelled AI-derived candidate fishing zones based on SST & chlorophyll.
        """
        if not self.is_configured():
            return DataUnavailableResult(
                category="marine",
                provider_name=self.name,
                reason="INCOIS base URL is unconfigured in environment.",
                is_configured=False,
            )

        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Check cache first
        cache_key = cache_keys.marine_pfz(latitude, longitude)
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data") and isinstance(cached["data"], list):
            try:
                records = [PFZRecord(**r) for r in cached["data"]]
                return records
            except Exception:
                pass

        # 2. Query centralized gateway
        gateway_res = await marine_data_gateway.get_fishing_zones(latitude, longitude)

        if not gateway_res.get("available") or not gateway_res.get("zones"):
            return DataUnavailableResult(
                category="marine",
                provider_name=self.name,
                reason="No candidate fishing zones available for coordinates.",
                is_configured=True,
            )

        records: List[PFZRecord] = []
        is_official = gateway_res.get("is_official_incois", False)
        provider_label = "Official-INCOIS" if is_official else "ORCA-Derived-PFZ"
        source_url = "https://incois.gov.in" if is_official else "https://marine-api.open-meteo.com"

        for z in gateway_res.get("zones", []):
            rec = PFZRecord(
                id=str(z.get("id", f"pfz-{latitude:.2f}-{longitude:.2f}")),
                geometry=PointGeometry(coordinates=(float(z.get("longitude", longitude)), float(z.get("latitude", latitude)))),
                sst_celsius=float(z["sst_celsius"]) if z.get("sst_celsius") is not None else None,
                chlorophyll_mg_m3=float(z["chlorophyll_mg_m3"]) if z.get("chlorophyll_mg_m3") is not None else None,
                depth_meters=None,
                bearing_degrees=None,
                distance_km=float(z.get("distance_km") or 15.0),
                valid_from=z.get("valid_from", now_str),
                valid_to=z.get("valid_to", now_str),
                source_url=source_url,
                provider=provider_label,
                retrieved_at=now_str,
            )
            records.append(rec)

        if records:
            await cache_client.set(
                cache_key,
                [r.model_dump() for r in records],
                ttl_seconds=settings.VALKEY_TTL_PFZ_SECONDS,
            )

        return records


incois_adapter = INCOISAdapter()
