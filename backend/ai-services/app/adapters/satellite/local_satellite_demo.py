"""
Local Demo Satellite Ocean-Color & Sea-Surface Temperature Adapter.
Loads verified offline benchmark datasets from app/data/satellite/satellite_demo.json.
CRITICAL INVARIANT:
- Clearly flags data_status="demo"
- Never claims demo data is live
- Exposes dataset timestamp and license
"""
import json
import math
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
    from app.schemas.normalized import SatelliteObservation
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import SatelliteObservation
    from ...observability.logger import logger

_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "satellite" / "satellite_demo.json"


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class LocalSatelliteDemoProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="Local-Satellite-Demo-Dataset",
            category="satellite",
            base_url="local://data/satellite",
            requires_api_key=False,
        )
        self.metadata: Dict[str, Any] = {}
        self.observations: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        try:
            if _DATA_FILE.exists():
                with open(_DATA_FILE, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    self.metadata = content.get("dataset_metadata", {})
                    self.observations = content.get("observations", [])
                logger.info(f"Loaded {len(self.observations)} satellite demo records.")
        except Exception as e:
            logger.warning(f"Failed to load satellite demo dataset: {e}")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "healthy" if self.observations else "empty",
            "mode": "demo_offline_sample",
            "records": len(self.observations),
            "timestamp": self.metadata.get("timestamp"),
            "license": self.metadata.get("license"),
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> List[SatelliteObservation]:
        """Fetch SST and Chlorophyll-a records for nearest location."""
        if not self.observations:
            return []

        # Find nearest point
        nearest = None
        min_dist = float("inf")
        for obs in self.observations:
            dist = _haversine(latitude, longitude, obs["latitude"], obs["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest = obs

        # If too far (> 250km from any demo station)
        if not nearest or min_dist > 250.0:
            return []

        now_str = datetime.now(timezone.utc).isoformat()
        dataset_ts = self.metadata.get("timestamp", "2026-09-20T12:00:00Z")

        sst_obs = SatelliteObservation(
            variable="sea_surface_temperature",
            value=nearest.get("sea_surface_temp_celsius"),
            units="celsius",
            latitude=nearest["latitude"],
            longitude=nearest["longitude"],
            observation_time=dataset_ts,
            product_time=now_str,
            resolution=self.metadata.get("spatial_resolution", "1km"),
            dataset="Copernicus-SST-L4-NRT-Demo",
            provider=self.name,
            source_url="local://data/satellite/satellite_demo.json",
            data_status="demo",
            confidence=0.75,
        )

        chl_obs = SatelliteObservation(
            variable="chlorophyll_a",
            value=nearest.get("chlorophyll_a_mg_m3"),
            units="mg/m3",
            latitude=nearest["latitude"],
            longitude=nearest["longitude"],
            observation_time=dataset_ts,
            product_time=now_str,
            resolution=self.metadata.get("spatial_resolution", "1km"),
            dataset="NASA-MODIS-Aqua-Chlorophyll-L3-Demo",
            provider=self.name,
            source_url="local://data/satellite/satellite_demo.json",
            data_status="demo",
            confidence=0.75,
        )

        return [sst_obs, chl_obs]

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": self.metadata.get("source", "Copernicus / NASA Demo Dataset"),
            "url": "local://data/satellite/satellite_demo.json",
            "license": self.metadata.get("license", "CC BY 4.0"),
            "notice": self.metadata.get("notice", "DEMO DATASET — Non-live research data."),
            "type": "self_hostable_dataset",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return self.metadata.get("timestamp")

    def get_confidence(self, response: Any) -> float:
        return 0.75


local_satellite_demo_provider = LocalSatelliteDemoProvider()
