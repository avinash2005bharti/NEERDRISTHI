import pytest
from app.integrations.incois_adapter import INCOISAdapter
from app.integrations.weather_adapter import WeatherAdapter
from app.integrations.tide_adapter import TideAdapter
from app.integrations.geocoder_adapter import GeocoderAdapter
from app.schemas.adapters import DataUnavailableResult


@pytest.mark.asyncio
async def test_incois_adapter_unconfigured_returns_unavailable():
    adapter = INCOISAdapter()
    adapter.base_url = ""
    adapter.pfz_endpoint = ""

    result = await adapter.fetch_pfz(13.08, 80.27)
    assert isinstance(result, DataUnavailableResult)
    assert result.category == "marine"
    assert result.is_configured is False
    assert "unconfigured" in result.reason.lower()


@pytest.mark.asyncio
async def test_weather_adapter_unconfigured_returns_unavailable():
    adapter = WeatherAdapter()
    adapter.base_url = ""
    adapter.forecast_endpoint = ""

    result = await adapter.fetch_weather_and_waves(13.08, 80.27)
    assert isinstance(result, DataUnavailableResult)
    assert result.category == "weather"
    assert result.is_configured is False


@pytest.mark.asyncio
async def test_tide_adapter_unconfigured_returns_unavailable():
    adapter = TideAdapter()
    adapter.base_url = ""
    adapter.tide_endpoint = ""

    result = await adapter.fetch_tide(13.08, 80.27)
    assert isinstance(result, DataUnavailableResult)
    assert result.category == "tide"
    assert result.is_configured is False


@pytest.mark.asyncio
async def test_geocoder_adapter_unconfigured_returns_unavailable():
    adapter = GeocoderAdapter()
    adapter.base_url = ""
    adapter.geocoder_endpoint = ""

    result = await adapter.resolve_place_name("Chennai Harbor")
    assert isinstance(result, DataUnavailableResult)
    assert result.category == "geospatial"
    assert result.is_configured is False
