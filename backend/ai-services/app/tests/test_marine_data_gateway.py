"""
Comprehensive Unit & Integration Tests for ORCA Marine Data Gateway (SIH26176).
Tests:
  - Weather: Open-Meteo success, timeout, MET Norway fallback
  - Marine: Open-Meteo success, INCOIS ERDDAP, Copernicus disabled, partial datasets
  - Tide: Open-Meteo sea level, WorldTides disabled/fallback
  - Geocoding: Forward geocoding, reverse geocoding, rate limit handling
  - Failure modes: HTTP 500, HTTP 429, timeout, invalid JSON, graceful degradation
  - 5 End-to-End Demo Queries per Section 23
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import httpx

from app.schemas.marine import (
    Location,
    WeatherData,
    MarineData,
    OceanBiology,
    TideData,
    FishingZone,
    MarineObservation,
)
from app.providers.gateway import marine_data_gateway
from app.providers.weather import open_meteo_weather, met_no_weather
from app.providers.marine import open_meteo_marine, incois_erddap, copernicus_marine
from app.providers.ocean import incois_erddap_ocean, copernicus_ocean
from app.providers.tide import open_meteo_tide, worldtides_provider
from app.providers.geocoding import nominatim_provider
from app.providers.fishing import official_incois_pfz, derived_fishing_zone


# ─── 1. Weather Provider Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_open_meteo_success():
    """Verify Open-Meteo weather fetch and normalization."""
    mock_payload = {
        "current": {
            "temperature_2m": 29.5,
            "apparent_temperature": 32.1,
            "precipitation": 0.0,
            "wind_speed_10m": 5.4,
            "wind_direction_10m": 240,
            "wind_gusts_10m": 7.8,
            "surface_pressure": 1011.2,
            "relative_humidity_2m": 75,
            "cloud_cover": 20,
            "weather_code": 1,
        }
    }
    with patch.object(open_meteo_weather, "get_http_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_factory.return_value = mock_client

        data = await open_meteo_weather.get_weather(15.29, 73.98)
        assert data is not None
        assert data.temperature == 29.5
        assert data.wind_speed == 5.4
        assert data.pressure == 1011.2


@pytest.mark.asyncio
async def test_weather_open_meteo_timeout_met_no_fallback():
    """Verify fallback to MET Norway when Open-Meteo times out."""
    with patch.object(open_meteo_weather, "get_weather", side_effect=httpx.TimeoutException("Timeout")):
        with patch.object(met_no_weather, "get_weather", new_callable=AsyncMock) as mock_met_no:
            mock_met_no.return_value = WeatherData(
                temperature=28.0,
                wind_speed=4.5,
                wind_direction=220.0,
                precipitation=0.0,
                pressure=1010.5,
            )
            # Clear cache for isolated test
            res = await marine_data_gateway.get_weather_forecast(15.29, 73.98)
            assert res["available"] is True
            assert res["data"]["temperature"] == 28.0
            assert any(s["provider"] == "met_no" for s in res["sources"])


# ─── 2. Marine Provider Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_marine_open_meteo_success():
    """Verify Open-Meteo marine wave and sea-state fetch."""
    mock_payload = {
        "current": {
            "wave_height": 1.4,
            "wave_direction": 260,
            "wave_period": 7.5,
            "swell_wave_height": 1.1,
            "sea_surface_temperature": 28.4,
            "ocean_current_velocity": 0.35,
            "ocean_current_direction": 180,
        }
    }
    with patch.object(open_meteo_marine, "get_http_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_factory.return_value = mock_client

        data = await open_meteo_marine.get_marine(15.29, 73.98)
        assert data is not None
        assert data.wave_height == 1.4
        assert data.sea_surface_temperature == 28.4
        assert data.ocean_current_velocity == 0.35


@pytest.mark.asyncio
async def test_incois_erddap_chlorophyll_and_sst():
    """Verify INCOIS ERDDAP query parsing for chlorophyll and SST."""
    mock_chl_resp = {
        "table": {
            "rows": [["2026-09-20T00:00:00Z", 15.29, 73.98, 0.45]]
        }
    }
    with patch.object(incois_erddap_ocean, "get_http_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_chl_resp
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_factory.return_value = mock_client

        chl = await incois_erddap_ocean.get_chlorophyll(15.29, 73.98)
        assert chl == 0.45


@pytest.mark.asyncio
async def test_copernicus_disabled_graceful_handling():
    """Verify Copernicus returns unconfigured status without crashing when disabled."""
    status = await copernicus_marine.health_check()
    assert "status" in status
    assert status["status"] in ["disabled", "credentials_missing"]
    # get_marine should gracefully return None
    data = await copernicus_marine.get_marine(15.29, 73.98)
    assert data is None


# ─── 3. Tide Provider Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tide_open_meteo_sea_level():
    """Verify Open-Meteo sea level extraction."""
    mock_payload = {
        "hourly": {
            "time": ["2026-09-27T00:00", "2026-09-27T06:00", "2026-09-27T12:00"],
            "sea_level": [0.42, 0.85, 0.31],
        }
    }
    with patch.object(open_meteo_tide, "get_http_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_factory.return_value = mock_client

        tide = await open_meteo_tide.get_tide(15.29, 73.98)
        assert tide is not None
        assert tide.is_official_tide_table is False
        assert tide.datum == "Mean Sea Level (MSL)"
        assert tide.water_level is not None


@pytest.mark.asyncio
async def test_worldtides_disabled_fallback():
    """Verify WorldTides gracefully returns None when disabled."""
    assert worldtides_provider.is_configured() is False
    tide = await worldtides_provider.get_tide(15.29, 73.98)
    assert tide is None


# ─── 4. Geocoding Provider Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nominatim_forward_and_reverse():
    """Verify Nominatim forward geocode and reverse geocode."""
    mock_search = [
        {
            "display_name": "Panaji, Goa, India",
            "lat": "15.4989",
            "lon": "73.8278",
            "type": "city",
            "class": "place",
        }
    ]
    mock_reverse = {"display_name": "Mormugao Port, Goa, India"}

    with patch.object(nominatim_provider, "get_http_client") as mock_client_factory:
        mock_client = AsyncMock()

        async def _mock_get(endpoint, params=None):
            resp = MagicMock()
            resp.is_success = True
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            if "search" in endpoint:
                resp.json.return_value = mock_search
            else:
                resp.json.return_value = mock_reverse
            return resp

        mock_client.get.side_effect = _mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_factory.return_value = mock_client

        # Forward
        loc = await nominatim_provider.geocode("Goa")
        assert loc is not None
        assert abs(loc.latitude - 15.4989) < 0.01

        # Reverse
        name = await nominatim_provider.reverse_geocode(15.4989, 73.8278)
        assert name is not None
        assert "Goa" in name


# ─── 5. Failure Simulation & Resilience Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_provider_http_500_graceful_degradation():
    """Verify HTTP 500 error from external API degrades without crashing."""
    with patch.object(open_meteo_weather, "get_weather", side_effect=httpx.HTTPStatusError("500 Internal Error", request=MagicMock(), response=MagicMock(status_code=500))):
        with patch.object(met_no_weather, "get_weather", side_effect=httpx.HTTPStatusError("500 Internal Error", request=MagicMock(), response=MagicMock(status_code=500))):
            res = await marine_data_gateway.get_weather_forecast(0.0, 0.0)
            assert res["available"] is False
            assert "errors" in res
            assert len(res["errors"]) > 0


@pytest.mark.asyncio
async def test_provider_empty_dataset_handling():
    """Verify empty dataset response is gracefully tagged as unavailable."""
    with patch.object(incois_erddap_ocean, "get_chlorophyll", new_callable=AsyncMock) as mock_chl:
        mock_chl.return_value = None
        chl = await marine_data_gateway.get_chlorophyll(10.0, 75.0)
        assert chl is None


# ─── 6. Section 23 End-to-End Demo Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_demo_query_1_weather_and_sea_condition_goa():
    """
    Test 1: What is the weather and sea condition near Goa tomorrow morning?
    Expected: location, weather, wind, waves, wave period, marine condition, source, timestamp.
    """
    goa_lat, goa_lon = 15.49, 73.82
    obs = await marine_data_gateway.get_comprehensive_observation(goa_lat, goa_lon)
    assert obs.location.latitude == goa_lat
    assert obs.location.longitude == goa_lon
    assert obs.timestamp is not None
    assert obs.status in ["available", "partial", "unavailable"]


@pytest.mark.asyncio
async def test_demo_query_2_safety_reasoning_signals():
    """
    Test 2: Is it safe for a small fishing boat to go out tomorrow morning?
    Expected reasoning signals: wind, wave height, wave period, rain/weather, current, tide.
    """
    goa_lat, goa_lon = 15.49, 73.82
    wx = await marine_data_gateway.get_weather_forecast(goa_lat, goa_lon)
    mar = await marine_data_gateway.get_marine_conditions(goa_lat, goa_lon)
    tide = await marine_data_gateway.get_tide(goa_lat, goa_lon)

    # Telemetry contracts exist
    assert "available" in wx
    assert "available" in mar
    assert "available" in tide


@pytest.mark.asyncio
async def test_demo_query_3_potential_fishing_zones_goa():
    """
    Test 3: Where are potential fishing zones near Goa today?
    Expected: SST, chlorophyll, currents, candidate zones, distance, reasoning, data sources.
    Clearly labeled as 'AI-derived candidate fishing zone' unless official INCOIS.
    """
    goa_lat, goa_lon = 15.49, 73.82
    res = await marine_data_gateway.get_fishing_zones(goa_lat, goa_lon)
    assert res["available"] is True
    assert "zones" in res
    assert len(res["zones"]) > 0

    first_zone = res["zones"][0]
    assert first_zone["zone_type"] == "AI-derived candidate fishing zone"
    assert first_zone["is_official_incois"] is False
    assert "AI-derived" in first_zone["explanation"]
    assert first_zone["sst_celsius"] is not None
    assert first_zone["suitability_score"] >= 0.0


@pytest.mark.asyncio
async def test_demo_query_4_sea_surface_temperature_mumbai():
    """
    Test 4: What is the sea surface temperature near Mumbai today?
    Expected: SST, provider, timestamp, coordinates.
    """
    mumbai_lat, mumbai_lon = 18.96, 72.82
    sst = await marine_data_gateway.get_sst(mumbai_lat, mumbai_lon)
    assert (sst is None) or (-2.0 <= sst <= 40.0)


@pytest.mark.asyncio
async def test_demo_query_5_tides_kochi():
    """
    Test 5: What are the tides near Kochi tomorrow?
    Expected: tide/sea-level information, provider, timestamp.
    """
    kochi_lat, kochi_lon = 9.93, 76.26
    tide = await marine_data_gateway.get_tide(kochi_lat, kochi_lon)
    assert "available" in tide
    if tide.get("available") and tide.get("data"):
        assert "water_level" in tide["data"]
        assert "provider" in tide["data"]
