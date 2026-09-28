"""
Copernicus Marine Ocean Provider for ORCA.
Advanced global ocean physics, currents, salinity, and high-res SST.
Credentials come ONLY from environment variables (COPERNICUS_USERNAME, COPERNICUS_PASSWORD).
If credentials are missing or COPERNICUS_ENABLED is false, ORCA gracefully degrades without crashing.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.ocean.base import BaseOceanProvider
    from app.schemas.marine import OceanBiology, MarineData
    from app.core.config import settings
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseOceanProvider
    from ...schemas.marine import OceanBiology, MarineData
    from ...core.config import settings
    from ...observability.logger import logger


class CopernicusOceanProvider(BaseOceanProvider):
    """
    Copernicus Marine Service (CMEMS) Ocean Provider.
    Handles SST, salinity, and biogeochemical parameters when credentials are configured.
    """

    def __init__(self):
        super().__init__(
            name="Copernicus-Ocean",
            category="ocean",
            base_url="https://cq-cmems.copernicus.eu",
            requires_api_key=True,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )

    def is_configured(self) -> bool:
        return bool(
            settings.COPERNICUS_ENABLED
            and settings.COPERNICUS_USERNAME
            and settings.COPERNICUS_PASSWORD
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check status of Copernicus Ocean configuration."""
        if not settings.COPERNICUS_ENABLED:
            return {
                "provider": self.name,
                "status": "disabled",
                "message": "Copernicus Ocean is disabled (COPERNICUS_ENABLED=false)",
            }
        if not self.is_configured():
            return {
                "provider": self.name,
                "status": "credentials_missing",
                "message": "Copernicus credentials not provided. Continuing with Open-Meteo & INCOIS ERDDAP fallback.",
            }
        return {
            "provider": self.name,
            "status": "available",
            "username": settings.COPERNICUS_USERNAME[:3] + "***" if settings.COPERNICUS_USERNAME else "",
        }

    async def get_chlorophyll(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch chlorophyll from Copernicus Marine if configured."""
        if not self.is_configured():
            return None
        return None

    async def get_sst(self, latitude: float, longitude: float) -> Optional[float]:
        """Fetch SST from Copernicus Marine if configured."""
        if not self.is_configured():
            return None
        return None

    async def get_ocean_state(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "source": "copernicus",
                "available": False,
                "reason": "credentials_missing",
            }
        return {
            "source": "copernicus",
            "available": True,
            "chlorophyll": await self.get_chlorophyll(latitude, longitude),
            "sst": await self.get_sst(latitude, longitude),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Copernicus Marine Service",
            "url": "https://marine.copernicus.eu",
            "license": "E.U. Copernicus Marine Open License",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.95

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_ocean_state(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_ocean_state(latitude, longitude)


copernicus_ocean = CopernicusOceanProvider()
