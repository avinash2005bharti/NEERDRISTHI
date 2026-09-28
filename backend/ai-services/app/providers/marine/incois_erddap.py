"""
INCOIS ERDDAP Public Ocean Data Provider for ORCA.
Accesses real public datasets on the official INCOIS ERDDAP server.
Base URL: https://erddap.incois.gov.in/erddap
No API key required for public ERDDAP machine-readable endpoints.
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
    from app.providers.marine.base import BaseMarineProvider
    from app.schemas.marine import MarineData, OceanBiology
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseMarineProvider
    from ...schemas.marine import MarineData, OceanBiology
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class INCOISErddapProvider(BaseMarineProvider):
    """
    INCOIS ERDDAP Ocean Science Provider.
    Queries verified public INCOIS ERDDAP datasets for chlorophyll, SST, and ocean physical variables.
    """

    KNOWN_DATASETS = {
        "chlorophyll": "IRS_chlorophyll_datasets",
        "oceansat2": "incois_oceansat2_datasets",
        "sst": "incois_argo_sst_weekly",
        "avhrr_sst": "NOAA_AVHRR_AMSR_datasets",
        "wind": "ascat_daily_datasets",
    }

    def __init__(self):
        super().__init__(
            name="INCOIS-ERDDAP",
            category="marine",
            base_url=settings.INCOIS_ERDDAP_BASE_URL or "https://erddap.incois.gov.in/erddap",
            requires_api_key=False,
            rate_limit_per_second=2.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Verify reachability of INCOIS ERDDAP server."""
        if not settings.INCOIS_ERDDAP_ENABLED:
            return {"provider": self.name, "status": "disabled"}

        try:
            async with self.get_http_client(timeout=5.0) as client:
                res = await client.get(
                    f"{self.base_url}/tabledap/allDatasets.json",
                    params={"datasetID": "allDatasets"},
                )
                return {
                    "provider": self.name,
                    "status": "healthy" if res.status_code == 200 else "degraded",
                    "code": res.status_code,
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "degraded",
                "error": str(e),
            }

    async def get_chlorophyll(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch chlorophyll-a concentration from INCOIS ERDDAP."""
        if not settings.INCOIS_ERDDAP_ENABLED:
            return None

        dataset_id = self.KNOWN_DATASETS["chlorophyll"]
        url = f"{self.base_url}/griddap/{dataset_id}.json"

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                # Query nearest grid point in ERDDAP
                resp = await client.get(
                    url,
                    params={
                        "chlorophyll": f"[({round(latitude, 2)})][({round(longitude, 2)})]"
                    },
                )
                if resp.status_code != 200:
                    return {"available": False, "source": "incois-erddap", "reason": "dataset unavailable"}
                return resp.json()

        try:
            res = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            if isinstance(res, dict) and not res.get("available", True):
                return None
            rows = res.get("table", {}).get("rows", [])
            if rows and len(rows) > 0 and rows[0][-1] is not None:
                return float(rows[0][-1])
            return None
        except Exception as e:
            logger.warning(f"[{self.name}] Chlorophyll query failed for ({latitude}, {longitude}): {e}")
            return None

    async def get_sst(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch Sea Surface Temperature from INCOIS ERDDAP."""
        if not settings.INCOIS_ERDDAP_ENABLED:
            return None

        dataset_id = self.KNOWN_DATASETS["sst"]
        url = f"{self.base_url}/tabledap/{dataset_id}.json"

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    url,
                    params={
                        "temperature,time,latitude,longitude": None,
                        f"latitude>=": round(latitude - 0.5, 2),
                        f"latitude<=": round(latitude + 0.5, 2),
                        f"longitude>=": round(longitude - 0.5, 2),
                        f"longitude<=": round(longitude + 0.5, 2),
                    },
                )
                if resp.status_code != 200:
                    return {"available": False, "source": "incois-erddap", "reason": "dataset unavailable"}
                return resp.json()

        try:
            res = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            if isinstance(res, dict) and not res.get("available", True):
                return None
            rows = res.get("table", {}).get("rows", [])
            if rows and len(rows) > 0 and rows[0][0] is not None:
                return float(rows[0][0])
            return None
        except Exception as e:
            logger.warning(f"[{self.name}] SST query failed for ({latitude}, {longitude}): {e}")
            return None

    async def get_marine(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[MarineData]:
        """Retrieve ERDDAP ocean observations into MarineData model."""
        sst = await self.get_sst(latitude, longitude)
        if sst is not None:
            return MarineData(sea_surface_temperature=sst)
        return None

    async def get_ocean_biology(self, latitude: float, longitude: float) -> Optional[OceanBiology]:
        """Retrieve chlorophyll observations into OceanBiology model."""
        chl = await self.get_chlorophyll(latitude, longitude)
        if chl is not None:
            return OceanBiology(chlorophyll=chl)
        return None

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return {
            "source": "incois-erddap",
            "available": settings.INCOIS_ERDDAP_ENABLED,
            "chlorophyll": await self.get_chlorophyll(latitude, longitude),
            "sst": await self.get_sst(latitude, longitude),
        }


incois_erddap = INCOISErddapProvider()
