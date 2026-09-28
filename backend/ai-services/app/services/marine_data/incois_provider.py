"""
INCOIS Marine Data Provider for ORCA (SIH26176).
Interacts with official INCOIS (Indian National Centre for Ocean Information Services)
bulletins, ERDDAP datasets, and PFZ advisories.
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from .base_provider import MarineDataProvider

try:
    from ...integrations.incois_adapter import incois_adapter
    from ...core.config import settings
except (ImportError, ValueError):
    from app.integrations.incois_adapter import incois_adapter
    from app.core.config import settings


class INCOISMarineProvider(MarineDataProvider):
    """
    Official Indian Government Ocean Information provider.
    Marks all successfully retrieved data as 'LIVE' with 'INCOIS' attribution.
    """

    def __init__(self):
        super().__init__(name="INCOIS", is_live_source=True)

    def is_available(self) -> bool:
        return bool(settings.is_incois_configured and getattr(settings, "INCOIS_API_KEY", None))

    async def get_sst(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_available() or lat is None or lon is None:
            return None
        try:
            import asyncio
            pfz_res = await asyncio.wait_for(
                incois_adapter.fetch_pfz(latitude=lat, longitude=lon),
                timeout=2.0
            )
            if isinstance(pfz_res, list) and pfz_res:
                sst = pfz_res[0].sst_celsius
                return {
                    "type": "FeatureCollection",
                    "metadata": {
                        "layer": "sea_surface_temperature",
                        "status": "LIVE",
                        "is_live": True,
                        "source": "INCOIS ERDDAP",
                        "unit": "°C",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {
                                "variable": "sst",
                                "value": sst,
                                "unit": "°C",
                                "status": "LIVE",
                                "source": "INCOIS ERDDAP",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        }
                    ]
                }
        except Exception:
            pass
        return None

    async def get_chlorophyll(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_available() or lat is None or lon is None:
            return None
        try:
            import asyncio
            pfz_res = await asyncio.wait_for(
                incois_adapter.fetch_pfz(latitude=lat, longitude=lon),
                timeout=2.0
            )
            if isinstance(pfz_res, list) and pfz_res:
                chl = pfz_res[0].chlorophyll_mg_m3
                return {
                    "type": "FeatureCollection",
                    "metadata": {
                        "layer": "chlorophyll_a",
                        "status": "LIVE",
                        "is_live": True,
                        "source": "INCOIS Ocean Colour",
                        "unit": "mg/m³",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {
                                "variable": "chlorophyll_a",
                                "value": chl,
                                "unit": "mg/m³",
                                "status": "LIVE",
                                "source": "INCOIS Ocean Colour",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        }
                    ]
                }
        except Exception:
            pass
        return None

    async def get_waves(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    async def get_wind(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    async def get_tides(
        self,
        lat: float,
        lon: float,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    async def get_pfz(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_available() or lat is None or lon is None:
            return None
        try:
            import asyncio
            records = await asyncio.wait_for(
                incois_adapter.fetch_pfz(latitude=lat, longitude=lon),
                timeout=2.0
            )
            if isinstance(records, list) and records:
                features = []
                for rec in records:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [rec.longitude, rec.latitude],
                        },
                        "properties": {
                            "id": rec.id,
                            "type": "PFZ",
                            "confidence": 0.90,
                            "sst_celsius": rec.sst_celsius,
                            "chlorophyll_mg_m3": rec.chlorophyll_mg_m3,
                            "depth_m": rec.depth_meters,
                            "distance_km": rec.distance_km,
                            "bearing_deg": rec.bearing_degrees,
                            "valid_from": rec.valid_from,
                            "valid_to": rec.valid_to,
                            "status": "LIVE",
                            "source": "INCOIS Official PFZ Advisory",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    })
                return {
                    "type": "FeatureCollection",
                    "metadata": {
                        "layer": "potential_fishing_zones",
                        "status": "LIVE",
                        "is_live": True,
                        "source": "INCOIS",
                        "zone_count": len(features),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "features": features,
                }
        except Exception:
            pass
        return None

    async def get_risk(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    async def get_overview(
        self,
        lat: float,
        lon: float,
    ) -> Optional[Dict[str, Any]]:
        return None
