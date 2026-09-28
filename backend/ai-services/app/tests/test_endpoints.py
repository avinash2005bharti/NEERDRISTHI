"""
FastAPI Endpoints Integration Tests for ORCA Open Data Layer.
All network endpoints are mocked to guarantee fast, reliable, offline testing.
Tests all public endpoints:
- GET /health
- GET /providers
- GET /weather/forecast
- GET /marine/forecast
- GET /tide
- GET /satellite/observations
- GET /alerts
- GET /fishing-zone/estimate
- POST /safety/assess
- GET /data-sources
- GET /demo/status
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.schemas.normalized import WeatherForecast, MarineForecast, TideObservation, MarineAlert

client = TestClient(app)


def test_get_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "providers" in data


def test_get_providers():
    res = client.get("/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "weather" in data["providers"]
    assert "marine" in data["providers"]
    assert "geocoding" in data["providers"]
    assert "tide" in data["providers"]


def test_get_weather_forecast_invalid_coordinates():
    # Lat > 90
    res = client.get("/weather/forecast", params={"latitude": 95.0, "longitude": 72.8})
    assert res.status_code == 422


def test_get_weather_forecast_valid():
    with patch("app.providers.registry.provider_registry.fetch_weather_forecast", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = WeatherForecast(
            location="Mumbai Coast",
            latitude=18.98,
            longitude=72.83,
            timezone="Asia/Kolkata",
            issued_at="2026-09-27T12:00:00Z",
            valid_from="2026-09-27T12:00:00Z",
            valid_to="2026-09-27T18:00:00Z",
            hourly_values={"wind_speed_10m": [5.5, 6.0]},
            units={"wind_speed_10m": "m/s"},
            provider="Open-Meteo Weather API",
            source_url="https://api.open-meteo.com/v1/forecast",
            data_status="forecast",
            confidence=0.92,
        )
        res = client.get("/weather/forecast", params={"latitude": 18.98, "longitude": 72.83})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["data"]["latitude"] == 18.98
        assert data["provider"] == "Open-Meteo Weather API"


def test_get_marine_forecast():
    with patch("app.providers.registry.provider_registry.fetch_marine_forecast", new_callable=AsyncMock) as mock_mar:
        mock_mar.return_value = MarineForecast(
            location="Offshore Mumbai",
            latitude=18.98,
            longitude=72.83,
            issued_at="2026-09-27T12:00:00Z",
            valid_from="2026-09-27T12:00:00Z",
            valid_to="2026-09-27T18:00:00Z",
            wave_height=1.2,
            wave_period=6.5,
            wind_speed=5.2,
            provider="Open-Meteo Marine API",
            source_url="https://marine-api.open-meteo.com/v1/marine",
            data_status="forecast",
            confidence=0.88,
        )
        res = client.get("/marine/forecast", params={"latitude": 18.98, "longitude": 72.83})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["data"]["wave_height"] == 1.2


def test_get_tide_local_dataset():
    # Mumbai coordinates
    res = client.get("/tide", params={"latitude": 18.98, "longitude": 72.83})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"]["water_level"] is not None
    assert "Mumbai" in data["data"]["station"]


def test_get_tide_oceanic_unavailable():
    with patch("app.providers.registry.provider_registry.fetch_tide", new_callable=AsyncMock) as mock_tide:
        mock_tide.return_value = {
            "status": "DATA_UNAVAILABLE",
            "category": "tide",
            "reason": "No configured tide provider for this location",
        }
        res = client.get("/tide", params={"latitude": 0.0, "longitude": 70.0})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DATA_UNAVAILABLE"
        assert "No configured tide provider" in data["reason"]


def test_get_satellite_observations():
    res = client.get("/satellite/observations", params={"latitude": 18.98, "longitude": 72.83})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["count"] >= 2
    assert data["data_status"] == "demo"


def test_get_alerts():
    with patch("app.providers.registry.provider_registry.fetch_alerts", new_callable=AsyncMock) as mock_alerts:
        mock_alerts.return_value = [
            MarineAlert(
                alert_id="GDACS-99",
                issuing_agency="GDACS",
                event_type="Tropical Storm",
                severity="Moderate",
                urgency="Immediate",
                certainty="Observed",
                affected_area="Arabian Sea",
                issue_time="2026-09-27T10:00:00Z",
                instruction="Exercise caution.",
                official_url="https://www.gdacs.org",
            )
        ]
        res = client.get("/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["alerts"]) == 1


def test_get_fishing_zone_estimate():
    with patch("app.providers.registry.provider_registry.fetch_weather_forecast", new_callable=AsyncMock) as mock_wx:
        mock_wx.return_value = WeatherForecast(
            location="Mumbai Coast",
            latitude=18.98,
            longitude=72.83,
            timezone="Asia/Kolkata",
            issued_at="2026-09-27T12:00:00Z",
            valid_from="2026-09-27T12:00:00Z",
            valid_to="2026-09-27T18:00:00Z",
            hourly_values={"wind_speed_10m": [5.0]},
            units={},
            provider="Open-Meteo",
            source_url="https://open-meteo.com",
            data_status="forecast",
            confidence=0.9,
        )
        res = client.get("/fishing-zone/estimate", params={"latitude": 18.98, "longitude": 72.83})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        est = data["data"]
        assert "suitability_score" in est
        assert "experimental fishing-zone suitability" in est["category"]
        assert "DISCLAIMER" in est["indicators_disclaimer"]


def test_post_safety_assess():
    with patch("app.providers.registry.provider_registry.fetch_weather_forecast", new_callable=AsyncMock) as mock_wx, \
         patch("app.providers.registry.provider_registry.fetch_marine_forecast", new_callable=AsyncMock) as mock_mar, \
         patch("app.providers.registry.provider_registry.fetch_tide", new_callable=AsyncMock) as mock_tide, \
         patch("app.providers.registry.provider_registry.fetch_alerts", new_callable=AsyncMock) as mock_alt:

        mock_wx.return_value = WeatherForecast(
            location="Mumbai",
            latitude=18.98,
            longitude=72.83,
            timezone="UTC",
            issued_at="2026-09-27T12:00:00Z",
            valid_from="2026-09-27T12:00:00Z",
            valid_to="2026-09-27T18:00:00Z",
            hourly_values={"wind_speed_10m": [4.5]},
            provider="Open-Meteo",
            source_url="https://open-meteo.com",
            data_status="forecast",
        )
        mock_mar.return_value = MarineForecast(
            location="Mumbai",
            latitude=18.98,
            longitude=72.83,
            issued_at="2026-09-27T12:00:00Z",
            valid_from="2026-09-27T12:00:00Z",
            valid_to="2026-09-27T18:00:00Z",
            wave_height=0.9,
            wind_speed=4.5,
            provider="Open-Meteo Marine",
            source_url="https://marine-api.open-meteo.com",
            data_status="forecast",
        )
        mock_tide.return_value = TideObservation(
            station="Mumbai Port",
            station_id="IN-MUM-01",
            observed_or_predicted="predicted",
            timestamp="2026-09-27T12:00:00Z",
            water_level=2.1,
            provider="Local-Tide",
            source_url="https://mumbaiport.gov.in",
            data_status="prediction",
        )
        mock_alt.return_value = []

        req_body = {
            "latitude": 18.98,
            "longitude": 72.83,
            "vessel_class": "motorized_fiberglass",
            "language": "hi",
        }
        res = client.post("/safety/assess", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assessment = data["assessment"]
        assert assessment["decision"] in ["GO", "CAUTION", "NO_GO", "DATA_UNAVAILABLE"]
        assert "explanations" in assessment
        assert "hi" in assessment["explanations"]
        assert "en" in assessment["explanations"]
        assert "mr" in assessment["explanations"]


def test_get_data_sources():
    res = client.get("/data-sources")
    assert res.status_code == 200
    data = res.json()
    assert "data_sources" in data
    sources = data["data_sources"]
    names = [s["name"] for s in sources]
    assert "Open-Meteo Weather API" in names
    assert "Open-Meteo Marine API" in names
    assert "Nominatim / OpenStreetMap" in names


def test_get_demo_status():
    res = client.get("/demo/status")
    assert res.status_code == 200
    data = res.json()
    assert "demo_mode" in data
    assert "configured_providers" in data
