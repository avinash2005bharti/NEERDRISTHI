"""
Adapters Package for ORCA Open Data Providers.
Initializes and registers all weather, marine, geocoding, tide, satellite, and alert providers.
"""
import sys
from pathlib import Path

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.registry import provider_registry
    # Weather
    from app.adapters.weather.open_meteo_weather import open_meteo_weather_provider
    from app.adapters.weather.fallbacks import noaa_gfs_provider, ecmwf_weather_provider
    # Marine
    from app.adapters.marine.open_meteo_marine import open_meteo_marine_provider
    from app.adapters.marine.fallbacks import copernicus_marine_provider, noaa_wave_provider
    # Geocoding
    from app.adapters.geocoding.nominatim import nominatim_geocoder_provider
    from app.adapters.geocoding.photon import photon_geocoder_provider
    # Tide
    from app.adapters.tide.official_tide import official_tide_provider
    from app.adapters.tide.noaa_coops import noaa_coops_tide_provider
    from app.adapters.tide.fes_tpxo import fes_tpxo_tide_provider
    from app.adapters.tide.local_tide_dataset import local_tide_dataset_provider
    from app.adapters.tide.water_level_fallback import water_level_fallback_provider
    # Satellite & PFZ
    from app.adapters.satellite.local_satellite_demo import local_satellite_demo_provider
    from app.adapters.satellite.satellite_sources import copernicus_satellite_provider, nasa_earthdata_provider, generic_erddap_provider
    from app.adapters.satellite.pfz_estimator import pfz_estimator
    # Alerts
    from app.adapters.alerts.gdacs_alerts import gdacs_alert_provider
    from app.adapters.alerts.alert_sources import imd_alert_provider, noaa_nhc_alert_provider, computed_risk_alert_provider
except (ImportError, ValueError):
    from ..providers.registry import provider_registry
    # Weather
    from .weather.open_meteo_weather import open_meteo_weather_provider
    from .weather.fallbacks import noaa_gfs_provider, ecmwf_weather_provider
    # Marine
    from .marine.open_meteo_marine import open_meteo_marine_provider
    from .marine.fallbacks import copernicus_marine_provider, noaa_wave_provider
    # Geocoding
    from .geocoding.nominatim import nominatim_geocoder_provider
    from .geocoding.photon import photon_geocoder_provider
    # Tide
    from .tide.official_tide import official_tide_provider
    from .tide.noaa_coops import noaa_coops_tide_provider
    from .tide.fes_tpxo import fes_tpxo_tide_provider
    from .tide.local_tide_dataset import local_tide_dataset_provider
    from .tide.water_level_fallback import water_level_fallback_provider
    # Satellite & PFZ
    from .satellite.local_satellite_demo import local_satellite_demo_provider
    from .satellite.satellite_sources import copernicus_satellite_provider, nasa_earthdata_provider, generic_erddap_provider
    from .satellite.pfz_estimator import pfz_estimator
    # Alerts
    from .alerts.gdacs_alerts import gdacs_alert_provider
    from .alerts.alert_sources import imd_alert_provider, noaa_nhc_alert_provider, computed_risk_alert_provider


def register_all_providers():
    """Register all available providers in the centralized registry."""
    # Weather
    provider_registry.register("weather", "open_meteo", open_meteo_weather_provider)
    provider_registry.register("weather", "noaa_gfs", noaa_gfs_provider)
    provider_registry.register("weather", "ecmwf", ecmwf_weather_provider)

    # Marine
    provider_registry.register("marine", "open_meteo", open_meteo_marine_provider)
    provider_registry.register("marine", "copernicus", copernicus_marine_provider)
    provider_registry.register("marine", "noaa_wave", noaa_wave_provider)

    # Geocoding
    provider_registry.register("geocoding", "nominatim", nominatim_geocoder_provider)
    provider_registry.register("geocoding", "photon", photon_geocoder_provider)

    # Tide
    provider_registry.register("tide", "official", official_tide_provider)
    provider_registry.register("tide", "noaa_coops", noaa_coops_tide_provider)
    provider_registry.register("tide", "fes_tpxo", fes_tpxo_tide_provider)
    provider_registry.register("tide", "local_dataset", local_tide_dataset_provider)
    provider_registry.register("tide", "water_level_fallback", water_level_fallback_provider)

    # Satellite
    provider_registry.register("satellite", "demo", local_satellite_demo_provider)
    provider_registry.register("satellite", "copernicus", copernicus_satellite_provider)
    provider_registry.register("satellite", "nasa", nasa_earthdata_provider)
    provider_registry.register("satellite", "erddap", generic_erddap_provider)

    # Alerts
    provider_registry.register("alerts", "gdacs", gdacs_alert_provider)
    provider_registry.register("alerts", "imd", imd_alert_provider)
    provider_registry.register("alerts", "noaa_nhc", noaa_nhc_alert_provider)
    provider_registry.register("alerts", "computed", computed_risk_alert_provider)


# Auto-register on import
register_all_providers()
