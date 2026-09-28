"""
NOAA/NCEP Global Forecast System (GFS) & ECMWF Open Data Fallback Adapters.
Document requirements, access patterns, and return DATA_UNAVAILABLE when unconfigured.
Never fabricate data.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.schemas.normalized import WeatherForecast
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import WeatherForecast
    from ...observability.logger import logger


class NOAAGFSWeatherProvider(BaseProvider):
    """
    NOAA/NCEP GFS Open Data Adapter.
    Source: NOAA National Centers for Environmental Prediction (NCEP) NOMADS / AWS Open Data.
    Authentication: Public / None required for NOMADS HTTP Open Data.
    Coverage: Global (0.25 degree resolution).
    """

    def __init__(self, base_url: str = ""):
        super().__init__(
            name="NOAA-NCEP-GFS",
            category="weather",
            base_url=base_url or "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_fallback",
            "message": "NOAA NOMADS GFS adapter is an optional binary GRIB2/OPeNDAP fallback.",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("NOAA GFS OPeNDAP/NOMADS client not configured in environment.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("NOAA GFS OPeNDAP/NOMADS client not configured in environment.")

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NOAA / NWS / NCEP",
            "url": "https://www.ncep.noaa.gov/",
            "license": "U.S. Public Domain",
            "notice": "Data provided by the National Oceanic and Atmospheric Administration (NOAA).",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.85


class ECMWFOpenDataProvider(BaseProvider):
    """
    ECMWF Open Data Adapter.
    Source: European Centre for Medium-Range Weather Forecasts (ECMWF).
    Registration: Free access under CC-BY 4.0; requires ecmwf-opendata client or S3 open data bucket.
    """

    def __init__(self, base_url: str = ""):
        super().__init__(
            name="ECMWF-Open-Data",
            category="weather",
            base_url=base_url or "https://data.ecmwf.int/forecasts",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_fallback",
            "message": "ECMWF Open Data requires AWS/Azure open bucket client or ecmwf-opendata library.",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("ECMWF open data client not configured in environment.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("ECMWF open data client not configured in environment.")

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "ECMWF",
            "url": "https://www.ecmwf.int/",
            "license": "Creative Commons Attribution 4.0 International (CC-BY-4.0)",
            "notice": "ECMWF Open Data. Copyright ECMWF.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.90


noaa_gfs_provider = NOAAGFSWeatherProvider()
ecmwf_weather_provider = ECMWFOpenDataProvider()
