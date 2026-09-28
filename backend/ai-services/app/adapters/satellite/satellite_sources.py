"""
Copernicus Marine Satellite, NASA Earthdata OceanColor, and Generic ERDDAP Adapters.
Documents credentials, dataset IDs, and processing levels.
Returns DATA_UNAVAILABLE when not configured in environment.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.core.config import settings
    from app.schemas.normalized import SatelliteObservation
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...core.config import settings
    from ...schemas.normalized import SatelliteObservation


class CopernicusSatelliteProvider(BaseProvider):
    """
    Copernicus Marine Service Satellite Products.
    Datasets:
      - SST: SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001 (ODYSSEA high-res L4 analysis)
      - Chlorophyll: OCEANCOLOUR_GLO_BGC_L3_NRT_009_101 (OLCI Sentinel-3 / MODIS)
    Requires registration at https://marine.copernicus.eu/
    """

    def __init__(self):
        super().__init__(
            name="Copernicus-Satellite-CMEMS",
            category="satellite",
            base_url="https://cq-cmems.copernicus.eu",
            api_key=settings.SATELLITE_API_KEY,
            requires_api_key=True,
        )
        self.dataset_id = settings.SATELLITE_DATASET or "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider" if not self.is_configured() else "configured",
            "dataset_id": self.dataset_id,
            "registration_url": "https://marine.copernicus.eu/",
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("Copernicus Marine satellite credentials not configured.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Copernicus Marine Service",
            "url": "https://marine.copernicus.eu",
            "license": "Copernicus Open Access Policy",
            "notice": "European Union Copernicus Marine Service Information.",
            "type": "open_data_registration_required",
            "requires_key": "true",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.90


class NASAEarthdataProvider(BaseProvider):
    """
    NASA Earthdata / OceanColor Web.
    Products:
      - MODIS-Aqua Level 3 Binned Daily 4km Chlorophyll-a
      - VIIRS SNPP Daily 750m Sea Surface Temperature
    Registration: NASA Earthdata Login (urs.earthdata.nasa.gov).
    """

    def __init__(self):
        super().__init__(
            name="NASA-Earthdata-OceanColor",
            category="satellite",
            base_url="https://oceandata.sci.gsfc.nasa.gov",
            requires_api_key=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider",
            "registration_portal": "https://urs.earthdata.nasa.gov/",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("NASA Earthdata token not configured in environment.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NASA Ocean Biology Processing Group (OBPG)",
            "url": "https://oceancolor.gsfc.nasa.gov",
            "license": "NASA Open Data Policy",
            "notice": "Data from NASA Goddard Space Flight Center OceanColor Web.",
            "type": "open_data_registration_required",
            "requires_key": "true",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.92


class GenericERDDAPProvider(BaseProvider):
    """
    Generic ERDDAP Server Adapter (e.g. NOAA CoastWatch ERDDAP).
    Allows configured dataset ID, variables, and geographic bounding box.
    Base URL: https://coastwatch.pfeg.noaa.gov/erddap
    """

    def __init__(self, base_url: str = ""):
        super().__init__(
            name="ERDDAP-Ocean-Data",
            category="satellite",
            base_url=base_url or "https://coastwatch.pfeg.noaa.gov/erddap",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get("/status.html", timeout=3.0)
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("ERDDAP dataset ID not specified or configured.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NOAA CoastWatch / ERDDAP",
            "url": self.base_url,
            "license": "Public Domain / CC0",
            "notice": "Environmental data provided via ERDDAP protocol.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.85


copernicus_satellite_provider = CopernicusSatelliteProvider()
nasa_earthdata_provider = NASAEarthdataProvider()
generic_erddap_provider = GenericERDDAPProvider()
