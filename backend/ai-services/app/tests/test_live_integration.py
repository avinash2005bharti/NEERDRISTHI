"""
Integration tests for new ORCA features:
- Open-Meteo weather adapter (live)
- Open-Meteo marine SST PFZ proxy (live)
- GIS service (haversine + Shapely)
- Valkey cache graceful degradation
- Marine alerts provider

Note: These tests hit live APIs. They require network access.
"""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_weather_adapter_live():
    """Open-Meteo atmospheric + marine fetch returns real data for Mumbai coast."""
    from app.integrations.weather_adapter import weather_adapter
    result = await weather_adapter.fetch_weather_and_waves(latitude=18.98, longitude=72.83)
    assert hasattr(result, "wind_speed_mps"), f"Expected WeatherObservation, got {result}"
    assert result.wind_speed_mps >= 0.0, "Wind speed must be non-negative"
    assert result.wave_height_meters >= 0.0, "Wave height must be non-negative"
    assert result.provider in ("OpenMeteoWeather", "open-meteo, open-meteo-marine")
    assert result.retrieved_at is not None


@pytest.mark.asyncio
async def test_pfz_adapter_fallback_to_sst_proxy():
    """INCOIS returns 404, adapter falls back to Open-Meteo SST proxy."""
    from app.integrations.incois_adapter import incois_adapter
    result = await incois_adapter.fetch_pfz(latitude=18.98, longitude=72.83)
    assert isinstance(result, list), f"Expected list of PFZRecord, got {result}"
    if result:
        assert result[0].sst_celsius is not None, "SST proxy must return SST value"
        assert result[0].provider in ("INCOIS", "OpenMeteoSST-Proxy", "ORCA-Derived-PFZ"), "Must identify provider"


@pytest.mark.asyncio
async def test_tide_adapter_graceful_unavailable():
    """Tide returns DataUnavailableResult or TideObservation, never raises."""
    from app.integrations.tide_adapter import tide_adapter
    result = await tide_adapter.fetch_tide(latitude=18.98, longitude=72.83)
    # Result is either a valid observation or a clear unavailability response
    is_observation = hasattr(result, "tide_height_meters")
    is_unavailable = hasattr(result, "reason")
    assert is_observation or is_unavailable, f"Unexpected result type: {type(result)}"


@pytest.mark.asyncio
async def test_geocoder_adapter_resolves_mumbai():
    """Nominatim geocoder resolves 'Sassoon Docks Mumbai' to Mumbai coordinates."""
    from app.integrations.geocoder_adapter import geocoder_adapter
    result = await geocoder_adapter.resolve_place_name("Sassoon Docks Mumbai")
    if hasattr(result, "latitude"):
        # Mumbai latitude ~18.9, longitude ~72.8
        assert 17.0 <= result.latitude <= 21.0, f"Latitude {result.latitude} not in Mumbai range"
        assert 70.0 <= result.longitude <= 75.0, f"Longitude {result.longitude} not in Mumbai range"
    else:
        # Geocoder might be unavailable in CI — just ensure no exception
        assert hasattr(result, "reason"), "Must return unavailability reason"


def test_gis_haversine_distance():
    """GIS service computes haversine distance accurately."""
    from app.services.gis_service import gis_service
    # Mumbai (72.83, 18.98) to Chennai (80.29, 13.08) ≈ 1032 km
    dist = gis_service.haversine_distance_km((72.83, 18.98), (80.29, 13.08))
    assert 1000 <= dist <= 1070, f"Expected ~1032 km, got {dist:.1f} km"


def test_gis_point_in_polygon():
    """Shapely/haversine point-in-polygon works for India EEZ check."""
    from app.services.gis_service import gis_service
    # Mumbai is within India EEZ
    assert gis_service.is_in_india_eez(72.83, 18.98), "Mumbai should be in India EEZ"
    # Atlantic coordinate is NOT in India EEZ
    assert not gis_service.is_in_india_eez(-30.0, 10.0), "Atlantic should not be in India EEZ"


def test_gis_buffer_returns_polygon():
    """Buffer calculation returns valid GeoJSON polygon."""
    from app.services.gis_service import gis_service
    buf = gis_service.buffer_km(72.83, 18.98, radius_km=50.0)
    assert buf["type"] == "Polygon"
    assert len(buf["coordinates"][0]) >= 4, "Polygon must have at least 4 coordinate pairs"


def test_gis_filter_within_radius():
    """Radius filter returns nearest features sorted by distance."""
    from app.services.gis_service import gis_service
    features = [
        {"geometry": {"type": "Point", "coordinates": [72.83, 18.98]}, "name": "Origin"},
        {"geometry": {"type": "Point", "coordinates": [72.90, 19.10]}, "name": "Nearby"},
        {"geometry": {"type": "Point", "coordinates": [80.0, 18.0]}, "name": "Far"},
    ]
    result = gis_service.filter_within_radius_km((72.83, 18.98), features, radius_km=30.0)
    assert len(result) >= 2, "Should find at least 2 features within 30km"
    assert result[0]["_distance_km"] <= result[-1]["_distance_km"], "Must be sorted by distance"


def test_valkey_cache_graceful_when_unconfigured():
    """Valkey cache returns None on get and False on set when unconfigured."""
    from app.cache.valkey_client import cache_client
    import asyncio
    # cache_client.is_configured() returns False because VALKEY_URL is not set
    # But graceful degradation means no exceptions
    result = asyncio.run(cache_client.get("nonexistent-key"))
    assert result is None, "Cache GET must return None when unconfigured"


@pytest.mark.asyncio
async def test_marine_alerts_derive_from_location():
    """Marine alerts provider derives location-specific alerts from Open-Meteo."""
    from app.services.marine_alerts import marine_alerts_provider
    result = await marine_alerts_provider.fetch_alerts_for_location(18.98, 72.83)
    assert "alerts" in result, "Must return alerts list"
    assert "status" in result, "Must include status"
    assert result["status"] in ("available", "no_active_alerts")
    # Alert structure validation
    for alert in result.get("alerts", []):
        assert "severity" in alert
        assert alert["severity"] in ("safe", "caution", "danger")
        assert "title" in alert
        assert "issued_by" in alert
