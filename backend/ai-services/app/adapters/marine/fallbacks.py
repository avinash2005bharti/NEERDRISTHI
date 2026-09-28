"""
Copernicus Marine Service (CMEMS) & NOAA WaveWatch III Marine Fallbacks.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
except (ImportError, ValueError):
    from ...providers.base import BaseProvider


class CopernicusMarineProvider(BaseProvider):
    """
    Copernicus Marine Service (CMEMS).
    Requires registration: https://marine.copernicus.eu/
    Authentication: Username/Password or CAS token via copernicusmarine client.
    Product examples: GLOBAL_ANALYSISFORECAST_WAV_001_027 (Waves), SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001.
    """

    def __init__(self, api_key: str = ""):
        super().__init__(
            name="Copernicus-Marine-CMEMS",
            category="marine",
            base_url="https://cq-cmems.copernicus.eu",
            api_key=api_key,
            requires_api_key=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider",
            "message": "Copernicus Marine Service requires credentials (marine.copernicus.eu).",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("CMEMS credentials (username/password or token) unconfigured.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("CMEMS credentials unconfigured.")

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Copernicus Marine Service (CMEMS)",
            "url": "https://marine.copernicus.eu",
            "license": "E.U. Copernicus Marine Service Open License",
            "notice": "Generated using E.U. Copernicus Marine Service Information.",
            "type": "open_data_registration_required",
            "requires_key": "true",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.90


class NOAAWaveWatchProvider(BaseProvider):
    """
    NOAA WaveWatch III Global Ocean Wave Model.
    Source: NOAA NOMADS Open Data.
    Authentication: Public / None.
    """

    def __init__(self):
        super().__init__(
            name="NOAA-WaveWatch-III",
            category="marine",
            base_url="https://nomads.ncep.noaa.gov/pub/data/nccf/com/wave/prod",
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider",
            "message": "NOAA WaveWatch III binary GRIB2 parser requires specialized client.",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("NOAA WaveWatch III client unconfigured.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("NOAA WaveWatch III client unconfigured.")

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "NOAA / NWS / NCEP",
            "url": "https://polar.ncep.noaa.gov/waves/",
            "license": "U.S. Public Domain",
            "notice": "Data from NOAA WaveWatch III operational ocean wave model.",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.88


copernicus_marine_provider = CopernicusMarineProvider()
noaa_wave_provider = NOAAWaveWatchProvider()
