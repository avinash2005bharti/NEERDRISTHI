"""
Ocean Data Provider for ORCA (SIH26176).
Connects to Open-Meteo Marine API (ECMWF WAM & NOAA WaveWatch III).
Provides live wave, swell, sea state, and marine water temperature.
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from .base_provider import MarineDataProvider
from .coastal_network import coastal_network_service


class OceanDataProvider(MarineDataProvider):
    """
    Live Oceanographic Marine Data Provider.
    Outputs live wave height, dominant period, direction, swell, and SST
    across all coastal stations in India.
    """

    def __init__(self):
        super().__init__(name="Open-Meteo Marine", is_live_source=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def get_waves(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return await coastal_network_service.get_waves(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_sst(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return await coastal_network_service.get_sst(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_chlorophyll(self, bbox=None, lat=None, lon=None, time=None):
        return await coastal_network_service.get_chlorophyll(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_wind(self, bbox=None, lat=None, lon=None, time=None):
        return await coastal_network_service.get_wind(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_tides(self, lat: float, lon: float, time=None):
        return await coastal_network_service.get_tides(lat=lat, lon=lon, time_param=time)

    async def get_pfz(self, bbox=None, lat=None, lon=None, time=None):
        return await coastal_network_service.get_pfz(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_risk(self, bbox=None, lat=None, lon=None, time=None):
        return await coastal_network_service.get_risk(bbox=bbox, lat=lat, lon=lon, time=time)

    async def get_overview(self, lat: float, lon: float):
        return await coastal_network_service.get_overview(lat=lat, lon=lon)

    async def get_restricted_zones(self, bbox=None, lat=None, lon=None, radius_km=None):
        return await coastal_network_service.get_restricted_zones(
            bbox=bbox, lat=lat, lon=lon, radius_km=radius_km
        )

