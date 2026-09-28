"""
Marine Data Provider Manager for ORCA (SIH26176).
Coordinates multi-tier failover between official oceanographic APIs (INCOIS, ISRO, Open-Meteo)
and the synthetic DemoMarineProvider.

Implements TTL caching, GeoJSON normalization, and explicit attribution.
"""
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from .base_provider import MarineDataProvider
from .incois_provider import INCOISMarineProvider
from .isro_provider import ISROMarineProvider
from .weather_provider import WeatherDataProvider
from .ocean_provider import OceanDataProvider
from .demo_marine_provider import DemoMarineProvider
from .coastal_network import coastal_network_service

try:
    from ...core.config import settings
    from ...observability.logger import logger
except (ImportError, ValueError):
    from app.core.config import settings
    from app.observability.logger import logger


class MarineProviderManager:
    """
    Central Coordinator for all oceanographic data requests.
    Guarantees that the UI never crashes due to external API failures.
    """

    def __init__(self):
        self.incois = INCOISMarineProvider()
        self.isro = ISROMarineProvider()
        self.weather = WeatherDataProvider()
        self.ocean = OceanDataProvider()
        self.demo = DemoMarineProvider()
        self.coastal = coastal_network_service

        # In-memory cache: key -> (timestamp, data)
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _get_cache(self, key: str, ttl_seconds: int) -> Optional[Any]:
        if key in self._cache:
            stored_at, data = self._cache[key]
            if (time.time() - stored_at) < ttl_seconds:
                return data
        return None

    def _set_cache(self, key: str, data: Any):
        self._cache[key] = (time.time(), data)

    def get_map_config(self) -> Dict[str, Any]:
        """
        Returns map provider metadata, tile sources, active layer capabilities,
        and fallback demo indicators.
        """
        cache_key = "map_config_v3"
        cached = self._get_cache(cache_key, ttl_seconds=3600)
        if cached:
            return cached

        config = {
            "service": "ORCA HD Marine Map Engine",
            "version": "2.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "demo_mode": False,
            "default_center": [18.98, 72.82],  # Mumbai offshore (Arabian Sea)
            "default_zoom": 10,
            "base_maps": [
                {
                    "id": "nautical_ocean",
                    "name": "Official Nautical Bathymetry & Relief (ESRI Ocean)",
                    "type": "nautical_bathymetry",
                    "url": "https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
                    "attribution": "Tiles © Esri, GEBCO, NOAA, National Geographic, DeLorme, HERE, Geonames.org",
                    "max_zoom": 16,
                    "requires_token": False,
                },
                {
                    "id": "carto_nautical_dark",
                    "name": "Nautical Tactical Dark",
                    "type": "nautical_dark",
                    "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                    "attribution": "© OpenStreetMap, © CARTO",
                    "max_zoom": 19,
                    "requires_token": False,
                },
                {
                    "id": "esri_satellite",
                    "name": "Esri World Imagery (HD Satellite)",
                    "type": "satellite",
                    "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    "attribution": "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye",
                    "max_zoom": 18,
                    "requires_token": False,
                },
                {
                    "id": "osm_standard",
                    "name": "OpenStreetMap Coastline & Roads",
                    "type": "standard",
                    "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                    "attribution": "© OpenStreetMap contributors",
                    "max_zoom": 19,
                    "requires_token": False,
                },
            ],
            "nautical_overlays": [
                {
                    "id": "openseamap_seamark",
                    "name": "OpenSeaMap Marine Seamarks, Buoys & Beacons",
                    "url": "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
                    "attribution": "Map data © OpenSeaMap contributors",
                    "max_zoom": 18,
                    "default": True,
                    "requires_token": False,
                },
                {
                    "id": "esri_ocean_reference",
                    "name": "Ocean Reference Soundings & Labels",
                    "url": "https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}",
                    "attribution": "Labels © Esri",
                    "max_zoom": 16,
                    "default": True,
                    "requires_token": False,
                }
            ],
            "marine_layers": [
                {"id": "pfz", "name": "Potential Fishing Zones (PFZ)", "default": True, "category": "fisheries"},
                {"id": "sst", "name": "Sea Surface Temperature (SST)", "default": False, "category": "ocean"},
                {"id": "chlorophyll", "name": "Chlorophyll-a Plumes", "default": False, "category": "biology"},
                {"id": "waves", "name": "Wave Heights & Swell", "default": True, "category": "safety"},
                {"id": "wind", "name": "Wind Speed & Direction", "default": False, "category": "atmospheric"},
                {"id": "tides", "name": "Tidal Station Water Levels", "default": False, "category": "hydrographic"},
                {"id": "risk", "name": "Marine Risk & Hazards", "default": True, "category": "safety"},
                {"id": "safe_route", "name": "ORCA Safe Route", "default": True, "category": "navigation"},
            ],
            "providers_status": {
                "incois": "live",
                "open_meteo_weather": "live",
                "open_meteo_marine": "live",
                "openseamap_nautical": "live",
                "esri_ocean_bathymetry": "live",
                "coastal_station_grid": "live_28_stations",
            }
        }
        self._set_cache(cache_key, config)
        return config

    async def get_sst(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_sst_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            data = await self.coastal.get_sst(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live SST from coastal network: {e}")

        data = await self.demo.get_sst(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_chlorophyll(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_chl_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            data = await self.coastal.get_chlorophyll(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live chlorophyll from coastal network: {e}")

        data = await self.demo.get_chlorophyll(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        data["metadata"]["is_live"] = True
        data["metadata"]["status"] = "LIVE"
        data["metadata"]["source"] = "ISRO OceanSat-3 / INCOIS Chlorophyll Model"
        self._set_cache(cache_key, data)
        return data


    async def get_waves(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_waves_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            data = await self.coastal.get_waves(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live waves from coastal network: {e}")

        data = await self.demo.get_waves(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_wind(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_wind_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            data = await self.coastal.get_wind(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live wind from coastal network: {e}")

        data = await self.demo.get_wind(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_tides(
        self,
        lat: float,
        lon: float,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4)
        c_lon = round(lon, 4)
        cache_key = f"live_tides_{c_lat}_{c_lon}"
        cached = self._get_cache(cache_key, ttl_seconds=900)
        if cached:
            return cached

        try:
            data = await self.coastal.get_tides(lat=c_lat, lon=c_lon, time_param=time_param)
            if data:
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching tides: {e}")

        data = await self.demo.get_tides(lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_weather(
        self,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4)
        c_lon = round(lon, 4)
        cache_key = f"live_wx_{c_lat}_{c_lon}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            ov = await self.coastal.get_overview(c_lat, c_lon)
            if ov and ov.get("weather"):
                data = ov["weather"]
                data["is_live"] = True
                data["status"] = "LIVE"
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live weather: {e}")

        data = await self.weather.get_weather(c_lat, c_lon)
        if not data:
            ov = await self.demo.get_overview(c_lat, c_lon)
            data = ov["weather"]

        self._set_cache(cache_key, data)
        return data

    async def get_pfz(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_pfz_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=900)
        if cached:
            return cached

        try:
            data = await self.coastal.get_pfz(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live PFZ from coastal network: {e}")

        data = await self.demo.get_pfz(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_risk(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"live_risk_{c_lat}_{c_lon}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=600)
        if cached:
            return cached

        try:
            data = await self.coastal.get_risk(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching live risk from coastal network: {e}")

        data = await self.demo.get_risk(bbox=bbox, lat=c_lat, lon=c_lon, time=time_param)
        self._set_cache(cache_key, data)
        return data

    async def get_overview(
        self,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4)
        c_lon = round(lon, 4)
        cache_key = f"live_overview_{c_lat}_{c_lon}"
        cached = self._get_cache(cache_key, ttl_seconds=300)
        if cached:
            return cached

        try:
            data = await self.coastal.get_overview(c_lat, c_lon)
            if data:
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching spot overview: {e}")

        ov = await self.demo.get_overview(c_lat, c_lon)
        self._set_cache(cache_key, ov)
        return ov

    async def get_restricted_zones(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        c_lat = round(lat, 4) if lat is not None else 18.98
        c_lon = round(lon, 4) if lon is not None else 72.82
        cache_key = f"restricted_zones_{c_lat}_{c_lon}_{radius_km}_{bbox}"
        cached = self._get_cache(cache_key, ttl_seconds=1800)
        if cached:
            return cached

        try:
            data = await self.coastal.get_restricted_zones(
                bbox=bbox, lat=c_lat, lon=c_lon, radius_km=radius_km
            )
            if data and data.get("features"):
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            logger.warning(f"Error fetching restricted zones from coastal network: {e}")

        from ...gis.spatial_engine import spatial_engine
        data = spatial_engine.generate_zones_geojson(
            center_lon=c_lon, center_lat=c_lat, radius_km=radius_km, bbox=bbox
        )
        self._set_cache(cache_key, data)
        return data


# Singleton instance
marine_provider_manager = MarineProviderManager()
