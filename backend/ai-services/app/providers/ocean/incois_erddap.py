"""
INCOIS ERDDAP Ocean Science Provider for ORCA.
Accesses real public datasets on the official INCOIS ERDDAP server.
Base URL: https://erddap.incois.gov.in/erddap
No API key required for public ERDDAP machine-readable endpoints.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.ocean.base import BaseOceanProvider
    from app.schemas.marine import OceanBiology, MarineData
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseOceanProvider
    from ...schemas.marine import OceanBiology, MarineData
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class INCOISErddapOceanProvider(BaseOceanProvider):
    """
    INCOIS ERDDAP Ocean Science Provider.
    Queries verified public INCOIS ERDDAP datasets for chlorophyll and SST.
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
            name="INCOIS-ERDDAP-Ocean",
            category="ocean",
            base_url=settings.INCOIS_ERDDAP_BASE_URL or "https://erddap.incois.gov.in/erddap",
            requires_api_key=False,
            rate_limit_per_second=2.0,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )

    def is_configured(self) -> bool:
        return bool(settings.INCOIS_ERDDAP_ENABLED and self.base_url)

    async def health_check(self) -> Dict[str, Any]:
        """Verify reachability of INCOIS ERDDAP server."""
        if not settings.INCOIS_ERDDAP_ENABLED:
            return {"provider": self.name, "status": "disabled", "enabled": False}

        try:
            async with self.get_http_client(timeout=5.0) as client:
                res = await client.get(
                    f"{self.base_url}/tabledap/allDatasets.json",
                    params={"datasetID": "allDatasets"},
                )
                return {
                    "provider": self.name,
                    "status": "available" if res.status_code == 200 else "degraded",
                    "http_status": res.status_code,
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "unavailable",
                "error": str(e),
            }

    async def get_chlorophyll(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch chlorophyll-a concentration in mg/m³ from INCOIS ERDDAP."""
        if not self.is_configured():
            return None

        dataset_id = self.KNOWN_DATASETS["chlorophyll"]
        url = f"{self.base_url}/griddap/{dataset_id}.json"

        query_timeout = min(float(self.timeout_seconds), 6.0)

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=query_timeout) as client:
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
                val = float(rows[0][-1])
                # Filter invalid/masked fill values e.g. -999.0
                if val >= 0.0 and val < 100.0:
                    return val
            return None
        except Exception as e:
            logger.warning(f"[{self.name}] Chlorophyll query failed for ({latitude}, {longitude}): {e}")
            return None

    async def get_sst(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch Sea Surface Temperature (SST) in Celsius from INCOIS ERDDAP."""
        if not self.is_configured():
            return None

        dataset_id = self.KNOWN_DATASETS["sst"]
        url = f"{self.base_url}/tabledap/{dataset_id}.json"
        query_timeout = min(float(self.timeout_seconds), 6.0)

        async def _call() -> Dict[str, Any]:
            async with self.get_http_client(timeout=query_timeout) as client:
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
                val = float(rows[0][0])
                if -2.0 <= val <= 40.0:
                    return val
            return None
        except Exception as e:
            logger.warning(f"[{self.name}] SST query failed for ({latitude}, {longitude}): {e}")
            return None

    async def get_ocean_state(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve combined ocean state observations."""
        chl = await self.get_chlorophyll(latitude, longitude)
        sst = await self.get_sst(latitude, longitude)
        return {
            "source": "incois-erddap",
            "available": (chl is not None or sst is not None),
            "chlorophyll": chl,
            "sst": sst,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "INCOIS ERDDAP",
            "url": "https://erddap.incois.gov.in/erddap",
            "license": "Government of India Open Data",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.95

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_ocean_state(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_ocean_state(latitude, longitude)


incois_erddap_ocean = INCOISErddapOceanProvider()
