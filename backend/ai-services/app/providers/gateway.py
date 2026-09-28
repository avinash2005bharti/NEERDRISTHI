"""
Marine Data Gateway for ORCA (SIH26176).
Centralized access layer for all meteorological, oceanographic, and geospatial data feeds.
Strictly isolates LangGraph agents from raw external HTTP/API dependencies.

Coordinates:
  - Atmospheric Weather: Open-Meteo (Primary) -> MET Norway (Fallback)
  - Sea-State & Waves: Open-Meteo Marine (Primary) -> INCOIS ERDDAP / Copernicus
  - Ocean Physical State: INCOIS ERDDAP (Chlorophyll, SST) -> Copernicus Marine
  - Water-Level & Tide: Open-Meteo Marine (Modeled Sea-Level) <-> WorldTides (Optional)
  - Geocoding & Reverse: Nominatim (OpenStreetMap)
  - Fishing Zones: Official INCOIS PFZ (Optional/Institutional) -> Derived Fishing Zone (Algorithmic)
"""
import sys
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timezone, timedelta

_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.core.config import settings
    from app.core.security import redact_secrets
    from app.observability.logger import logger
    from app.cache.valkey_client import cache_client
    from app.schemas.marine import (
        Location,
        WeatherData,
        MarineData,
        OceanBiology,
        DataSource,
        MarineObservation,
        TideData,
        FishingZone,
    )
    from app.providers.weather import (
        OpenMeteoWeatherProvider,
        open_meteo_weather,
        MetNorwayWeatherProvider,
        met_no_weather,
    )
    from app.providers.marine import (
        OpenMeteoMarineProvider,
        open_meteo_marine,
        CopernicusMarineProvider,
        copernicus_marine,
        INCOISErddapProvider,
        incois_erddap,
    )
    from app.providers.ocean import (
        INCOISErddapOceanProvider,
        incois_erddap_ocean,
        CopernicusOceanProvider,
        copernicus_ocean,
    )
    from app.providers.tide import (
        OpenMeteoTideProvider,
        open_meteo_tide,
        WorldTidesProvider,
        worldtides_provider,
    )
    from app.providers.geocoding import (
        NominatimProvider,
        nominatim_provider,
    )
    from app.providers.fishing import (
        OfficialINCOISPFZProvider,
        official_incois_pfz,
        DerivedFishingZoneProvider,
        derived_fishing_zone,
    )
except (ImportError, ValueError):
    from ..core.config import settings
    from ..core.security import redact_secrets
    from ..observability.logger import logger
    from ..cache.valkey_client import cache_client
    from ..schemas.marine import (
        Location,
        WeatherData,
        MarineData,
        OceanBiology,
        DataSource,
        MarineObservation,
        TideData,
        FishingZone,
    )
    from .weather import (
        OpenMeteoWeatherProvider,
        open_meteo_weather,
        MetNorwayWeatherProvider,
        met_no_weather,
    )
    from .marine import (
        OpenMeteoMarineProvider,
        open_meteo_marine,
        CopernicusMarineProvider,
        copernicus_marine,
        INCOISErddapProvider,
        incois_erddap,
    )
    from .ocean import (
        INCOISErddapOceanProvider,
        incois_erddap_ocean,
        CopernicusOceanProvider,
        copernicus_ocean,
    )
    from .tide import (
        OpenMeteoTideProvider,
        open_meteo_tide,
        WorldTidesProvider,
        worldtides_provider,
    )
    from .geocoding import (
        NominatimProvider,
        nominatim_provider,
    )
    from .fishing import (
        OfficialINCOISPFZProvider,
        official_incois_pfz,
        DerivedFishingZoneProvider,
        derived_fishing_zone,
    )


class MarineDataGateway:
    """
    Central Gateway coordinating multi-tier provider fallbacks, caching,
    freshness checks, coordinate validation, and uniform normalization.
    """

    def __init__(self):
        # Weather providers
        self.weather_primary = open_meteo_weather
        self.weather_fallback = met_no_weather

        # Marine & ocean providers
        self.marine_primary = open_meteo_marine
        self.incois_erddap = incois_erddap
        self.copernicus = copernicus_marine

        # Ocean biology/physics providers
        self.ocean_erddap = incois_erddap_ocean
        self.ocean_copernicus = copernicus_ocean

        # Tide providers
        self.tide_primary = open_meteo_tide
        self.worldtides = worldtides_provider

        # Geocoder provider
        self.geocoder = nominatim_provider

        # Fishing zone providers
        self.pfz_official = official_incois_pfz
        self.pfz_derived = derived_fishing_zone

        # In-memory LRU / process cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    # ── Cache Helpers ────────────────────────────────────────────────────────

    async def _get_cache(self, key: str) -> Optional[Any]:
        """Fetch from Valkey (if configured and running) or in-memory fallback."""
        try:
            valkey_data = await cache_client.get(key)
            if valkey_data and "data" in valkey_data:
                return valkey_data["data"]
        except Exception:
            pass

        # In-memory check
        entry = self._memory_cache.get(key)
        if entry:
            if time.time() - entry["cached_at"] < entry["ttl"]:
                return entry["data"]
            del self._memory_cache[key]
        return None

    async def _set_cache(self, key: str, data: Any, ttl_seconds: int = 1800):
        """Store in Valkey (if available) and in-memory fallback."""
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        try:
            await cache_client.set(key, payload, ttl_seconds)
        except Exception:
            pass

        self._memory_cache[key] = {
            "cached_at": time.time(),
            "ttl": ttl_seconds,
            "data": data,
        }

    # ── Freshness & Provenance Helpers ───────────────────────────────────────

    def evaluate_freshness(self, timestamp_iso: Optional[str]) -> Tuple[str, int]:
        """Calculate freshness state ('fresh', 'stale', 'unavailable') and age in minutes."""
        if not timestamp_iso:
            return "unavailable", 0
        try:
            ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta_mins = max(0, int((now - ts).total_seconds() / 60.0))
            max_mins = getattr(settings, "MAX_DATA_FRESHNESS_MINUTES", 360)
            if delta_mins <= max_mins:
                return "fresh", delta_mins
            return "stale", delta_mins
        except Exception:
            return "fresh", 0

    # ── 1. Weather Forecast (Open-Meteo -> MET Norway) ───────────────────────

    async def get_weather_forecast(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch atmospheric weather with intelligent fallback.
        Chain: Open-Meteo -> MET Norway -> Graceful partial/unavailable.
        """
        lat_r = round(latitude, 3)
        lon_r = round(longitude, 3)
        hour_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        cache_key = f"orca:weather:{lat_r}:{lon_r}:{hour_tag}"

        cached = await self._get_cache(cache_key)
        if cached:
            logger.info(f"[Gateway] Weather Cache HIT for ({lat_r}, {lon_r})")
            if isinstance(cached, dict):
                return cached
            return {"available": True, "data": cached, "from_cache": True}

        errors: List[Dict[str, str]] = []
        sources: List[DataSource] = []
        weather_res: Optional[WeatherData] = None
        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Step A: Try Open-Meteo Weather
        t0 = time.time()
        try:
            weather_res = await self.weather_primary.get_weather(latitude, longitude, date)
            duration_ms = int((time.time() - t0) * 1000)
            if weather_res:
                logger.info(f"[Gateway] Open-Meteo weather OK ({duration_ms}ms) for ({lat_r}, {lon_r})")
                sources.append(
                    DataSource(
                        provider="open-meteo",
                        dataset="ECMWF/DWD-OpenMeteo",
                        retrieved_at=retrieved_at,
                        timestamp=retrieved_at,
                        confidence=0.92,
                        data_status="fresh",
                        freshness_minutes=0,
                        source_url="https://api.open-meteo.com",
                    )
                )
        except Exception as e:
            err_msg = redact_secrets(str(e))
            logger.warning(f"[Gateway] Open-Meteo weather failed: {err_msg}")
            errors.append({"provider": "open-meteo", "reason": err_msg})

        # Step B: Fallback to MET Norway if enabled and Open-Meteo failed
        if not weather_res and settings.ENABLE_PROVIDER_FALLBACK and settings.MET_NO_ENABLED:
            logger.info(f"[Gateway] Engaging MET Norway fallback for weather at ({lat_r}, {lon_r})")
            t0 = time.time()
            try:
                weather_res = await self.weather_fallback.get_weather(latitude, longitude, date)
                duration_ms = int((time.time() - t0) * 1000)
                if weather_res:
                    logger.info(f"[Gateway] MET Norway fallback OK ({duration_ms}ms) for ({lat_r}, {lon_r})")
                    sources.append(
                        DataSource(
                            provider="met_no",
                            dataset="Locationforecast/2.0",
                            retrieved_at=retrieved_at,
                            timestamp=retrieved_at,
                            confidence=0.90,
                            data_status="fresh",
                            freshness_minutes=0,
                            source_url="https://api.met.no",
                        )
                    )
            except Exception as e:
                err_msg = redact_secrets(str(e))
                logger.warning(f"[Gateway] MET Norway fallback failed: {err_msg}")
                errors.append({"provider": "met_no", "reason": err_msg})

        if weather_res:
            res_dict = {
                "available": True,
                "partial": False,
                "data": weather_res.model_dump(),
                "sources": [s.model_dump() for s in sources],
                "errors": errors,
                "timestamp": retrieved_at,
            }
            await self._set_cache(cache_key, res_dict, ttl_seconds=1800)
            return res_dict

        return {
            "available": False,
            "partial": False,
            "data": {},
            "sources": [],
            "errors": errors or [{"provider": "weather", "reason": "All weather providers unavailable"}],
            "timestamp": retrieved_at,
        }

    # ── 2. Marine Conditions (Open-Meteo Marine -> INCOIS ERDDAP -> Copernicus)

    async def get_marine_conditions(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch ocean sea-state (waves, swell, currents, SST).
        Chain: Open-Meteo Marine -> fill missing variables via INCOIS ERDDAP / Copernicus.
        """
        lat_r = round(latitude, 3)
        lon_r = round(longitude, 3)
        hour_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        cache_key = f"orca:marine:{lat_r}:{lon_r}:{hour_tag}"

        cached = await self._get_cache(cache_key)
        if cached:
            logger.info(f"[Gateway] Marine Cache HIT for ({lat_r}, {lon_r})")
            if isinstance(cached, dict):
                return cached
            return {"available": True, "data": cached, "from_cache": True}

        errors: List[Dict[str, str]] = []
        sources: List[DataSource] = []
        marine_res: Optional[MarineData] = None
        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Step A: Open-Meteo Marine
        t0 = time.time()
        try:
            marine_res = await self.marine_primary.get_marine(latitude, longitude, date)
            duration_ms = int((time.time() - t0) * 1000)
            if marine_res:
                logger.info(f"[Gateway] Open-Meteo marine OK ({duration_ms}ms) for ({lat_r}, {lon_r})")
                sources.append(
                    DataSource(
                        provider="open-meteo-marine",
                        dataset="ECMWF-WAM",
                        retrieved_at=retrieved_at,
                        timestamp=retrieved_at,
                        confidence=0.91,
                        data_status="fresh",
                        freshness_minutes=0,
                        source_url="https://marine-api.open-meteo.com",
                    )
                )
        except Exception as e:
            err_msg = redact_secrets(str(e))
            logger.warning(f"[Gateway] Open-Meteo marine error: {err_msg}")
            errors.append({"provider": "open_meteo_marine", "reason": err_msg})

        # Step B: If SST or currents are missing, query INCOIS ERDDAP
        if marine_res is None or marine_res.sea_surface_temperature is None:
            if settings.INCOIS_ERDDAP_ENABLED:
                try:
                    erddap_sst = await self.ocean_erddap.get_sst(latitude, longitude)
                    if erddap_sst is not None:
                        if marine_res is None:
                            marine_res = MarineData(sea_surface_temperature=erddap_sst)
                        else:
                            marine_res.sea_surface_temperature = erddap_sst
                        sources.append(
                            DataSource(
                                provider="incois-erddap",
                                dataset="incois_argo_sst_weekly",
                                retrieved_at=retrieved_at,
                                timestamp=retrieved_at,
                                confidence=0.95,
                                data_status="fresh",
                                freshness_minutes=0,
                                source_url="https://erddap.incois.gov.in/erddap",
                            )
                        )
                except Exception as e:
                    logger.warning(f"[Gateway] INCOIS ERDDAP SST enrichment error: {e}")

        # Step C: If Copernicus Marine configured and enabled, enrich further
        if self.copernicus.is_configured():
            try:
                cmems_data = await self.copernicus.get_marine(latitude, longitude, date)
                if cmems_data:
                    sources.append(
                        DataSource(
                            provider="copernicus",
                            dataset="CMEMS-GLOBAL",
                            retrieved_at=retrieved_at,
                            timestamp=retrieved_at,
                            confidence=0.95,
                            data_status="fresh",
                            freshness_minutes=0,
                            source_url="https://marine.copernicus.eu",
                        )
                    )
            except Exception as e:
                logger.warning(f"[Gateway] Copernicus Marine query error: {e}")

        if marine_res:
            res_dict = {
                "available": True,
                "partial": (marine_res.wave_height is None or marine_res.sea_surface_temperature is None),
                "data": marine_res.model_dump(),
                "sources": [s.model_dump() for s in sources],
                "errors": errors,
                "timestamp": retrieved_at,
            }
            await self._set_cache(cache_key, res_dict, ttl_seconds=1800)
            return res_dict

        return {
            "available": False,
            "partial": False,
            "data": {},
            "sources": [],
            "errors": errors or [{"provider": "marine", "reason": "Marine data currently unavailable"}],
            "timestamp": retrieved_at,
        }

    # ── 3. Ocean State (Chlorophyll & SST via INCOIS ERDDAP & Copernicus) ─────

    async def get_ocean_conditions(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch ocean biological and chemical state (chlorophyll-a, SST)."""
        lat_r = round(latitude, 3)
        lon_r = round(longitude, 3)
        date_tag = date or datetime.now(timezone.utc).strftime("%Y%m%d")
        cache_key = f"orca:ocean:{lat_r}:{lon_r}:{date_tag}"

        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        sources: List[DataSource] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        chl: Optional[float] = None
        sst: Optional[float] = None

        # Try INCOIS ERDDAP first (concurrently for low latency)
        if settings.INCOIS_ERDDAP_ENABLED:
            try:
                results = await asyncio.gather(
                    self.ocean_erddap.get_chlorophyll(latitude, longitude),
                    self.ocean_erddap.get_sst(latitude, longitude),
                    return_exceptions=True,
                )
                if not isinstance(results[0], BaseException):
                    chl = results[0]
                if not isinstance(results[1], BaseException):
                    sst = results[1]

                if chl is not None or sst is not None:
                    sources.append(
                        DataSource(
                            provider="incois-erddap",
                            dataset="IRS_chlorophyll_datasets / incois_argo_sst_weekly",
                            retrieved_at=retrieved_at,
                            timestamp=retrieved_at,
                            confidence=0.95,
                            data_status="fresh",
                            source_url="https://erddap.incois.gov.in/erddap",
                        )
                    )
            except Exception as e:
                logger.warning(f"[Gateway] INCOIS ERDDAP ocean query error: {e}")

        # Fallback for SST: Open-Meteo Marine provides sea_surface_temperature
        if sst is None:
            try:
                mar = await self.marine_primary.get_marine(latitude, longitude)
                if mar and mar.sea_surface_temperature is not None:
                    sst = mar.sea_surface_temperature
                    sources.append(
                        DataSource(
                            provider="open-meteo-marine",
                            dataset="SST-Model",
                            retrieved_at=retrieved_at,
                            timestamp=retrieved_at,
                            confidence=0.88,
                            data_status="fresh",
                            source_url="https://marine-api.open-meteo.com",
                        )
                    )
            except Exception as e:
                logger.warning(f"[Gateway] Fallback SST error: {e}")

        # Copernicus if configured
        if self.ocean_copernicus.is_configured():
            try:
                if chl is None:
                    chl = await self.ocean_copernicus.get_chlorophyll(latitude, longitude)
                if sst is None:
                    sst = await self.ocean_copernicus.get_sst(latitude, longitude)
            except Exception as e:
                logger.warning(f"[Gateway] Copernicus ocean query error: {e}")

        bio = OceanBiology(chlorophyll=chl)
        res_dict = {
            "available": (chl is not None or sst is not None),
            "chlorophyll": chl,
            "sea_surface_temperature": sst,
            "biology": bio.model_dump(),
            "sources": [s.model_dump() for s in sources],
            "timestamp": retrieved_at,
        }
        await self._set_cache(cache_key, res_dict, ttl_seconds=3600)
        return res_dict

    async def get_sst(self, latitude: float, longitude: float) -> Optional[float]:
        """Direct helper for SST."""
        state = await self.get_ocean_conditions(latitude, longitude)
        return state.get("sea_surface_temperature")

    async def get_chlorophyll(self, latitude: float, longitude: float) -> Optional[float]:
        """Direct helper for Chlorophyll-a."""
        state = await self.get_ocean_conditions(latitude, longitude)
        return state.get("chlorophyll")

    # ── 4. Tide & Water-Level (Open-Meteo <-> WorldTides) ─────────────────────

    async def get_tide(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch water-level / tide prediction with fallback.
        Priority:
          - If WORLDTIDES_ENABLED and configured: WorldTides -> Open-Meteo
          - Otherwise: Open-Meteo Marine sea-level (Modeled MSL)
        """
        lat_r = round(latitude, 3)
        lon_r = round(longitude, 3)
        date_tag = date or datetime.now(timezone.utc).strftime("%Y%m%d")
        cache_key = f"orca:tide:{lat_r}:{lon_r}:{date_tag}"

        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        tide_res: Optional[TideData] = None
        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Step A: WorldTides if enabled and configured
        if settings.WORLDTIDES_ENABLED and self.worldtides.is_configured():
            try:
                tide_res = await self.worldtides.get_tide(latitude, longitude, date)
            except Exception as e:
                logger.warning(f"[Gateway] WorldTides query failed: {e}")

        # Step B: Open-Meteo Marine modeled sea level
        if not tide_res:
            try:
                tide_res = await self.tide_primary.get_tide(latitude, longitude, date)
            except Exception as e:
                logger.warning(f"[Gateway] Open-Meteo tide query failed: {e}")

        if tide_res:
            res_dict = {
                "available": True,
                "data": tide_res.model_dump(),
                "timestamp": retrieved_at,
            }
            await self._set_cache(cache_key, res_dict, ttl_seconds=3600)
            return res_dict

        return {
            "available": False,
            "data": None,
            "reason": "Tide data currently unavailable for coordinates",
            "timestamp": retrieved_at,
        }

    # ── 5. Potential Fishing Zones (Official INCOIS PFZ <-> Derived) ──────────

    async def get_fishing_zones(
        self, latitude: float, longitude: float
    ) -> Dict[str, Any]:
        """
        Fetch fishing zone advisories.
        Uses Official INCOIS PFZ if configured, otherwise derives candidate zones from SST & CHL.
        """
        lat_r = round(latitude, 3)
        lon_r = round(longitude, 3)
        date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
        cache_key = f"orca:pfz:{lat_r}:{lon_r}:{date_tag}"

        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        retrieved_at = datetime.now(timezone.utc).isoformat()

        # Step A: Check official institutional INCOIS PFZ if configured
        if self.pfz_official.is_configured():
            try:
                official_zones = await self.pfz_official.get_fishing_zones(latitude, longitude)
                if official_zones:
                    res_dict = {
                        "available": True,
                        "source": "official_incois",
                        "is_official_incois": True,
                        "zone_type": "Official INCOIS PFZ",
                        "zones": [z.model_dump() for z in official_zones],
                        "timestamp": retrieved_at,
                    }
                    await self._set_cache(cache_key, res_dict, ttl_seconds=21600)
                    return res_dict
            except Exception as e:
                logger.warning(f"[Gateway] Official INCOIS PFZ fetch error: {e}")

        # Step B: AI-Derived Candidate Fishing Zones
        # Pull live SST and chlorophyll if available to feed the inference model
        sst = await self.get_sst(latitude, longitude)
        chl = await self.get_chlorophyll(latitude, longitude)
        marine = await self.get_marine_conditions(latitude, longitude)
        current_vel = (
            marine.get("data", {}).get("ocean_current_velocity")
            if marine.get("available")
            else None
        )

        derived_zones = await self.pfz_derived.get_fishing_zones(
            latitude=latitude,
            longitude=longitude,
            sst=sst,
            chlorophyll=chl,
            current_velocity=current_vel,
        )

        res_dict = {
            "available": True,
            "source": "ai_derived",
            "is_official_incois": False,
            "zone_type": "AI-derived candidate fishing zone",
            "zones": [z.model_dump() for z in derived_zones],
            "disclaimer": "AI-derived candidate fishing zone based on oceanographic thermal and biological signals. Not an official INCOIS PFZ bulletin.",
            "timestamp": retrieved_at,
        }
        await self._set_cache(cache_key, res_dict, ttl_seconds=14400)
        return res_dict

    # ── 6. Geocoding (Nominatim Forward & Reverse) ───────────────────────────

    async def geocode_location(self, place_name: str) -> Optional[Location]:
        """Geocode place name to coordinates."""
        return await self.geocoder.geocode(place_name)

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """Reverse geocode coordinates to place name."""
        return await self.geocoder.reverse_geocode(latitude, longitude)

    # ── 7. Provider Status & Health ──────────────────────────────────────────

    async def get_providers_status(self) -> Dict[str, Any]:
        """
        Aggregate operational status of all data providers.
        Complies with Section 19 of SIH26176 requirements.
        """
        open_meteo_health = await self.weather_primary.health_check()
        marine_health = await self.marine_primary.health_check()
        erddap_health = await self.incois_erddap.health_check()
        copernicus_health = await self.copernicus.health_check()
        met_no_health = await self.weather_fallback.health_check()
        worldtides_health = await self.worldtides.health_check()
        nominatim_health = await self.geocoder.health_check()
        incois_official_health = await self.pfz_official.health_check()

        def _clean_status(raw_status: str, is_enabled: bool = True) -> str:
            if not is_enabled:
                return "disabled"
            if raw_status in ["healthy", "available", "reachable"]:
                return "available"
            return raw_status

        return {
            "open_meteo": {
                "enabled": True,
                "status": _clean_status(open_meteo_health.get("status", "available")),
            },
            "open_meteo_marine": {
                "enabled": True,
                "status": _clean_status(marine_health.get("status", "available")),
            },
            "incois_erddap": {
                "enabled": settings.INCOIS_ERDDAP_ENABLED,
                "status": _clean_status(erddap_health.get("status", "available"), settings.INCOIS_ERDDAP_ENABLED),
            },
            "copernicus": {
                "enabled": settings.COPERNICUS_ENABLED,
                "status": (
                    "available"
                    if self.copernicus.is_configured()
                    else ("credentials_missing" if settings.COPERNICUS_ENABLED else "disabled")
                ),
            },
            "met_no": {
                "enabled": settings.MET_NO_ENABLED,
                "status": _clean_status(met_no_health.get("status", "available"), settings.MET_NO_ENABLED),
            },
            "worldtides": {
                "enabled": settings.WORLDTIDES_ENABLED,
                "status": (
                    "available"
                    if self.worldtides.is_configured()
                    else ("disabled" if not settings.WORLDTIDES_ENABLED else "credentials_missing")
                ),
            },
            "nominatim": {
                "enabled": True,
                "status": _clean_status(nominatim_health.get("status", "available")),
            },
            "incois_official_pfz": {
                "enabled": settings.INCOIS_OFFICIAL_ENABLED,
                "status": (
                    "available"
                    if self.pfz_official.is_configured()
                    else "unconfigured_optional_provider"
                ),
            },
        }

    async def get_comprehensive_observation(
        self, latitude: float, longitude: float
    ) -> MarineObservation:
        """
        Assemble normalized multi-domain MarineObservation model.
        Combines Weather, Marine, and Ocean Biology into a single contract.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        loc = Location(latitude=latitude, longitude=longitude)

        wx_resp = await self.get_weather_forecast(latitude, longitude)
        mar_resp = await self.get_marine_conditions(latitude, longitude)
        ocn_resp = await self.get_ocean_conditions(latitude, longitude)

        wx_data = WeatherData(**wx_resp["data"]) if wx_resp.get("available") and wx_resp.get("data") else None
        mar_data = MarineData(**mar_resp["data"]) if mar_resp.get("available") and mar_resp.get("data") else None
        ocn_data = OceanBiology(**ocn_resp.get("biology", {})) if ocn_resp.get("available") else None

        all_sources: List[DataSource] = []
        for s in wx_resp.get("sources", []):
            all_sources.append(DataSource(**s))
        for s in mar_resp.get("sources", []):
            all_sources.append(DataSource(**s))
        for s in ocn_resp.get("sources", []):
            all_sources.append(DataSource(**s))

        return MarineObservation(
            location=loc,
            timestamp=now_str,
            weather=wx_data,
            marine=mar_data,
            biology=ocn_data,
            sources=all_sources,
            status="available" if (wx_data or mar_data) else "unavailable",
        )


# Global singleton instance
marine_data_gateway = MarineDataGateway()
