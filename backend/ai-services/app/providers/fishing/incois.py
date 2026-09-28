"""
Official INCOIS PFZ Provider for ORCA.
Provides official government-issued Potential Fishing Zone (PFZ) advisories.
Only active when INCOIS_OFFICIAL_ENABLED=true and INCOIS_API_KEY is supplied.
If unconfigured, safely degrades without crashing.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.fishing.base import BaseFishingZoneProvider
    from app.schemas.marine import FishingZone, DataSource
    from app.core.config import settings
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseFishingZoneProvider
    from ...schemas.marine import FishingZone, DataSource
    from ...core.config import settings
    from ...observability.logger import logger


class OfficialINCOISPFZProvider(BaseFishingZoneProvider):
    """
    Official INCOIS PFZ Provider.
    Operates ONLY when official institutional credentials and endpoint are present.
    """

    def __init__(self):
        super().__init__(
            name="Official-INCOIS-PFZ",
            category="fishing",
            base_url=settings.INCOIS_BASE_URL or "",
            api_key=settings.INCOIS_API_KEY,
            requires_api_key=True,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        self.endpoint = settings.INCOIS_PFZ_ENDPOINT or "/pfz"

    def is_configured(self) -> bool:
        return bool(
            settings.INCOIS_OFFICIAL_ENABLED
            and self.base_url
            and self.api_key
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check status of official INCOIS PFZ provider."""
        if not settings.INCOIS_OFFICIAL_ENABLED:
            return {
                "provider": self.name,
                "status": "disabled",
                "message": "Official INCOIS PFZ is disabled (INCOIS_OFFICIAL_ENABLED=false)",
            }
        if not self.is_configured():
            return {
                "provider": self.name,
                "status": "credentials_missing",
                "message": "Institutional INCOIS API credentials not configured. Using AI-derived candidate fishing zones.",
            }
        return {
            "provider": self.name,
            "status": "available",
            "message": "Official INCOIS credentials configured.",
        }

    async def get_fishing_zones(
        self,
        latitude: float,
        longitude: float,
        sst: Optional[float] = None,
        chlorophyll: Optional[float] = None,
        current_velocity: Optional[float] = None,
    ) -> List[FishingZone]:
        """Fetch official PFZ advisories from INCOIS if institutional credentials configured."""
        if not self.is_configured():
            return []

        try:
            async with self.get_http_client(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    self.endpoint,
                    params={"latitude": latitude, "longitude": longitude},
                )
                if not resp.is_success:
                    return []
                data = resp.json()
                # Parse official bulletin records
                records: List[FishingZone] = []
                for item in data.get("zones", []):
                    records.append(
                        FishingZone(
                            id=item.get("id", f"incois-{latitude}-{longitude}"),
                            latitude=float(item.get("latitude", latitude)),
                            longitude=float(item.get("longitude", longitude)),
                            suitability_score=float(item.get("score", 90.0)),
                            confidence=0.98,
                            sst_celsius=float(item["sst"]) if "sst" in item else None,
                            chlorophyll_mg_m3=float(item["chlorophyll"]) if "chlorophyll" in item else None,
                            is_official_incois=True,
                            zone_type="Official INCOIS PFZ",
                            explanation="Official Potential Fishing Zone advisory issued by ESSO-INCOIS, Ministry of Earth Sciences, Govt. of India.",
                            valid_from=item.get("valid_from", datetime.now(timezone.utc).isoformat()),
                            valid_to=item.get("valid_to", datetime.now(timezone.utc).isoformat()),
                            sources=[
                                DataSource(
                                    provider="incois_official",
                                    dataset="ESSO-INCOIS-PFZ-Bulletin",
                                    source_url="https://incois.gov.in",
                                    confidence=0.98,
                                    data_status="fresh",
                                )
                            ],
                        )
                    )
                return records
        except Exception as e:
            logger.warning(f"[{self.name}] Failed fetching official INCOIS PFZ: {e}")
            return []

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "ESSO-INCOIS, Ministry of Earth Sciences",
            "url": "https://incois.gov.in",
            "license": "Government of India Official Advisory",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.98

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_fishing_zones(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_fishing_zones(latitude, longitude)


official_incois_pfz = OfficialINCOISPFZProvider()
