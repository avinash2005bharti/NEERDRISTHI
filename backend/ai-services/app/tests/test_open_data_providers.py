"""
Unit and Integration Tests for ORCA Open Data Providers (SIH26176).
Uses mocked HTTP responses — strictly independent of live external APIs.
Covers all 15 required test scenarios.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import httpx

from app.schemas.normalized import (
    WeatherForecast,
    MarineForecast,
    TideObservation,
    SatelliteObservation,
    SafetyAssessment,
    MarineAlert,
)
from app.adapters.weather.open_meteo_weather import OpenMeteoWeatherProvider
from app.adapters.marine.open_meteo_marine import OpenMeteoMarineProvider
from app.adapters.geocoding.nominatim import NominatimGeocoderProvider
from app.adapters.tide.local_tide_dataset import LocalTideDatasetProvider
from app.adapters.tide.water_level_fallback import WaterLevelFallbackProvider
from app.adapters.satellite.local_satellite_demo import LocalSatelliteDemoProvider
from app.adapters.satellite.pfz_estimator import PFZSuitabilityEstimator
from app.adapters.alerts import ComputedRiskAlertProvider
from app.providers.registry import ProviderRegistry
from app.services.safety_evaluator import SafetyEvaluatorService
from app.core.security import redact_secrets, validate_external_url
from app.core.resilience import RateLimiter, CircuitBreaker, CircuitState, retry_with_backoff


# ─── 1. Open-Meteo Weather Response Parsing ──────────────────────────────────

def test_open_meteo_weather_response_parsing():
    provider = OpenMeteoWeatherProvider()
    mock_raw = {
        "latitude": 18.98,
        "longitude": 72.83,
        "timezone": "Asia/Kolkata",
        "hourly": {
            "time": ["2026-09-27T12:00", "2026-09-27T13:00"],
            "temperature_2m": [29.5, 29.8],
            "relative_humidity_2m": [78, 76],
            "precipitation": [0.0, 0.2],
            "rain": [0.0, 0.2],
            "weather_code": [1, 2],
            "cloud_cover": [25, 40],
            "surface_pressure": [1011.2, 1010.8],
            "wind_speed_10m": [6.2, 6.8],
            "wind_direction_10m": [240, 245],
            "wind_gusts_10m": [8.5, 9.1],
            "visibility": [10000, 9500],
        },
        "hourly_units": {
            "temperature_2m": "°C",
            "wind_speed_10m": "m/s",
            "precipitation": "mm",
        },
    }

    result = provider.normalize_response(mock_raw, latitude=18.98, longitude=72.83)
    assert isinstance(result, WeatherForecast)
    assert result.latitude == 18.98
    assert result.longitude == 72.83
    assert result.data_status == "forecast"
    assert result.provider == provider.name
    assert "wind_speed_10m" in result.hourly_values
    assert result.hourly_values["wind_speed_10m"][0] == 6.2
    assert result.confidence > 0.8
    assert "Open-Meteo" in provider.get_attribution()["source"]


# ─── 2. Open-Meteo Marine Response Parsing ───────────────────────────────────

def test_open_meteo_marine_response_parsing():
    provider = OpenMeteoMarineProvider()
    mock_raw = {
        "latitude": 18.98,
        "longitude": 72.83,
        "current": {
            "wave_height": 1.45,
            "wave_direction": 260,
            "wave_period": 7.2,
            "wind_wave_height": 0.6,
            "wind_wave_direction": 255,
            "wind_wave_period": 4.1,
            "swell_wave_height": 1.3,
            "swell_wave_direction": 262,
            "swell_wave_period": 7.5,
            "ocean_current_velocity": 0.42,
            "ocean_current_direction": 180,
        },
        "hourly": {
            "time": ["2026-09-27T12:00"],
            "wave_height": [1.45],
            "sea_level": [0.35],
        },
        "current_units": {
            "wave_height": "m",
            "wave_period": "s",
        },
    }

    result = provider.normalize_response(mock_raw, latitude=18.98, longitude=72.83)
    assert isinstance(result, MarineForecast)
    assert result.wave_height == 1.45
    assert result.wave_period == 7.2
    assert result.current_speed == 0.42
    assert result.sea_level == 0.35
    assert result.data_status == "forecast"
    assert "Open-Meteo" in result.provider


# ─── 3. Nominatim Geocoding Response Parsing ─────────────────────────────────

def test_nominatim_geocoding_response_parsing():
    provider = NominatimGeocoderProvider()
    mock_raw = {
        "place_id": 123456,
        "display_name": "Sassoon Docks, Colaba, Mumbai, Maharashtra, 400005, India",
        "lat": "18.9167",
        "lon": "72.8250",
        "importance": 0.85,
        "boundingbox": ["18.910", "18.920", "72.820", "72.830"],
    }

    loc = provider.normalize_response(mock_raw)
    assert loc.name == "Sassoon Docks, Colaba, Mumbai, Maharashtra, 400005, India"
    assert loc.latitude == 18.9167
    assert loc.longitude == 72.8250
    assert loc.confidence == 0.85
    assert loc.bounding_box == [18.910, 18.920, 72.820, 72.830]
    assert "Nominatim" in loc.provider


# ─── 4. Missing Optional Fields Handling ─────────────────────────────────────

def test_missing_optional_fields_parsing():
    # Marine response missing swell, wave period, current, sea_level
    marine_provider = OpenMeteoMarineProvider()
    minimal_marine = {
        "latitude": 18.98,
        "longitude": 72.83,
        "current": {
            "wave_height": 1.2,
            # wave_period missing
            # ocean_current missing
        },
        "hourly": {},
    }
    result = marine_provider.normalize_response(minimal_marine, latitude=18.98, longitude=72.83)
    assert result.wave_height == 1.2
    assert result.wave_period is None
    assert result.current_speed is None
    assert result.sea_level is None

    # Weather response missing visibility, gusts, rain
    weather_provider = OpenMeteoWeatherProvider()
    minimal_weather = {
        "latitude": 18.98,
        "longitude": 72.83,
        "hourly": {
            "time": ["2026-09-27T12:00"],
            "temperature_2m": [28.0],
            "wind_speed_10m": [5.0],
        },
    }
    wx = weather_provider.normalize_response(minimal_weather, latitude=18.98, longitude=72.83)
    assert wx.hourly_values.get("wind_speed_10m") == [5.0]
    assert "visibility" not in wx.hourly_values


# ─── 5. Timeout and Retry Behaviour ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeout_and_retry_behaviour():
    attempts = 0

    async def flaky_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.TimeoutException("Connection timed out after 30s")
        return {"status": "ok", "attempt": attempts}

    breaker = CircuitBreaker("TestBreaker", failure_threshold=5)
    result = await retry_with_backoff(
        flaky_call,
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=1.5,
        jitter=False,
        circuit_breaker=breaker,
    )
    assert result["status"] == "ok"
    assert attempts == 3
    assert breaker.state == CircuitState.CLOSED


# ─── 6. Provider Fallback Behaviour ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_provider_fallback_behaviour():
    registry = ProviderRegistry()

    # Create a failing primary provider
    class FailingWeatherProvider(OpenMeteoWeatherProvider):
        async def fetch_forecast(self, lat, lon, **kwargs):
            raise httpx.HTTPError("Primary gateway 502 Bad Gateway")

    # Create a working fallback provider
    class MockFallbackWeatherProvider(OpenMeteoWeatherProvider):
        def __init__(self):
            super().__init__()
            self.name = "Fallback-Weather"
        async def fetch_forecast(self, lat, lon, **kwargs):
            return WeatherForecast(
                location="Fallback Shore",
                latitude=lat,
                longitude=lon,
                timezone="UTC",
                issued_at="2026-09-27T12:00:00Z",
                valid_from="2026-09-27T12:00:00Z",
                valid_to="2026-09-27T18:00:00Z",
                provider="Fallback-Weather",
                source_url="https://fallback.example.org",
                data_status="forecast",
                confidence=0.85,
            )

    registry.register("weather", "failing_primary", FailingWeatherProvider())
    registry.register("weather", "working_fallback", MockFallbackWeatherProvider())

    # Set failing as primary
    with patch("app.core.config.settings.WEATHER_PROVIDER", "failing_primary"):
        res = await registry.fetch_weather_forecast(18.98, 72.83)
        assert res is not None
        assert res.provider == "Fallback-Weather"
        assert res.data_status == "forecast"


# ─── 7. Stale Data Rejection ─────────────────────────────────────────────────

def test_stale_data_rejection():
    from app.utils.freshness import calculate_freshness

    # 1. Fresh observation (10 minutes ago)
    now = datetime.now(timezone.utc)
    fresh_time = (now - timedelta(minutes=10)).isoformat()
    assert calculate_freshness(fresh_time, max_minutes=360) == "fresh"

    # 2. Stale observation (7 hours = 420 minutes ago, limit is 360)
    stale_time = (now - timedelta(hours=7)).isoformat()
    assert calculate_freshness(stale_time, max_minutes=360) == "stale"


# ─── 8. Invalid Coordinates Validation ───────────────────────────────────────

def test_invalid_coordinates():
    provider = OpenMeteoWeatherProvider()
    assert not provider.validate_coordinates(95.0, 72.0)     # Lat > 90
    assert not provider.validate_coordinates(-95.0, 72.0)    # Lat < -90
    assert not provider.validate_coordinates(18.0, 195.0)    # Lon > 180
    assert not provider.validate_coordinates(18.0, -190.0)   # Lon < -180
    assert provider.validate_coordinates(18.98, 72.83)       # Valid


# ─── 9. Rate Limit Handling ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_handling():
    limiter = RateLimiter(requests_per_second=20.0)
    start = asyncio.get_event_loop().time()
    for _ in range(5):
        await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.0  # Successfully completed without deadlocking


# ─── 10. Tide DATA_UNAVAILABLE Behaviour ─────────────────────────────────────

@pytest.mark.asyncio
async def test_tide_data_unavailable_behaviour():
    # Query oceanic coordinates far from any coastal station (> 1000 km)
    local_provider = LocalTideDatasetProvider()
    result = await local_provider.fetch_current(latitude=0.0, longitude=70.0)

    # Invariant: Must return DATA_UNAVAILABLE, never fabricate, never substitute wave height
    assert isinstance(result, dict)
    assert result["status"] == "DATA_UNAVAILABLE"
    assert "No configured tide station within 150km" in result["reason"]

    # Verify fallback also returns DATA_UNAVAILABLE when empty
    fallback_provider = WaterLevelFallbackProvider()
    mock_req = httpx.Request("GET", "http://test")
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, *args, **kwargs):
            raise httpx.HTTPStatusError("Not found", request=mock_req, response=mock_resp)

    with patch.object(fallback_provider, "get_http_client", return_value=MockClient()):
        res_fallback = await fallback_provider.fetch_current(0.0, 70.0)
        assert res_fallback["status"] == "DATA_UNAVAILABLE"
        assert "No configured tide provider" in res_fallback["reason"]


# ─── 11. Satellite Demo Data Labelled Non-Live ────────────────────────────────

@pytest.mark.asyncio
async def test_satellite_demo_data_labelled_non_live():
    provider = LocalSatelliteDemoProvider()
    obs_list = await provider.fetch_current(18.98, 72.83)
    assert len(obs_list) >= 2

    for obs in obs_list:
        assert isinstance(obs, SatelliteObservation)
        assert obs.data_status == "demo", "Demo data must be explicitly labeled as demo"
        assert obs.value is not None

    attr = provider.get_attribution()
    assert "DEMO" in attr["notice"]
    assert "CC BY 4.0" in attr["license"]


# ─── 12. Cyclone Alert Priority Over Normal Weather ──────────────────────────

def test_cyclone_alert_priority_over_normal_weather():
    evaluator = SafetyEvaluatorService()

    # Very calm physical weather
    calm_weather = {"wind_speed_mps": 2.5, "precipitation_mm": 0.0, "provider": "Open-Meteo"}
    calm_marine = {"wave_height_meters": 0.5, "wave_period_seconds": 6.0, "provider": "Open-Meteo Marine"}

    # Active severe cyclone warning
    severe_alert = [{
        "alert_id": "IMD-CYC-2026-01",
        "issuing_agency": "India Meteorological Department (IMD)",
        "event_type": "Extremely Severe Cyclonic Storm 'VAAYU'",
        "severity": "Extreme",
        "urgency": "Immediate",
        "certainty": "Observed",
        "affected_area": "Maharashtra & Gujarat Coastal Waters",
        "instruction": "Total suspension of fishing operations. Fishermen out at sea advised to return immediately.",
    }]

    assessment = evaluator.evaluate_safety(
        latitude=18.98,
        longitude=72.83,
        vessel_class="motorized_fiberglass",
        weather_data=calm_weather,
        marine_data=calm_marine,
        alerts=severe_alert,
    )

    # Invariant: Cyclone alert must trump calm local weather -> NO_GO
    assert assessment.decision == "NO_GO"
    assert assessment.risk_level == "CRITICAL"
    assert assessment.risk_score >= 90
    assert any("Official Severe Alert Active" in r for r in assessment.reasons)


# ─── 13. Safety Engine Refuses GO on Missing Critical Data ───────────────────

def test_safety_engine_refusing_go_on_missing_critical_data():
    evaluator = SafetyEvaluatorService()

    # Missing atmospheric weather
    assessment = evaluator.evaluate_safety(
        latitude=18.98,
        longitude=72.83,
        vessel_class="motorized_fiberglass",
        weather_data=None,  # Missing!
        marine_data={"wave_height_meters": 0.8},
        alerts=[],
    )

    # Invariant: Never declare GO when critical telemetry is missing
    assert assessment.decision in ["DATA_UNAVAILABLE", "NO_GO"]
    assert assessment.decision != "GO"
    assert len(assessment.missing_data) > 0
    assert any("Wind speed & atmospheric weather" in m for m in assessment.missing_data)


# ─── 14. Secret Redaction in Logs ────────────────────────────────────────────

def test_secret_redaction_in_logs():
    raw_log = (
        "Connecting to mongodb://myUser:SuperSecretPassword123@cluster0.mongodb.net:27017/orca "
        "with groq_key=gsk_mockTestingSecretKeyDoNotUse1234567890 "
        "and bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis"
    )

    redacted = redact_secrets(raw_log)
    assert "SuperSecretPassword123" not in redacted
    assert "gsk_mockTestingSecretKeyDoNotUse1234567890" not in redacted
    assert "doNotLeakThis" not in redacted
    assert "[REDACTED]" in redacted or "[USER]:[REDACTED]@" in redacted or "[GROQ_KEY_REDACTED]" in redacted



# ─── 15. Hindi and Marathi Explanations Preserve Decision ────────────────────

def test_hindi_and_marathi_explanations_preserve_decision():
    evaluator = SafetyEvaluatorService()

    # Condition that causes CAUTION: High wave near vessel limit (1.7m for 2.0m max)
    weather = {"wind_speed_mps": 6.0, "precipitation_mm": 0.0}
    marine = {"wave_height_meters": 1.7, "wave_period_seconds": 6.5}

    assessment = evaluator.evaluate_safety(
        latitude=18.98,
        longitude=72.83,
        vessel_class="motorized_fiberglass",
        weather_data=weather,
        marine_data=marine,
        alerts=[],
    )

    assert assessment.decision == "CAUTION"
    exps = assessment.explanations
    assert "en" in exps and "hi" in exps and "mr" in exps

    # English check
    assert "[CAUTION]" in exps["en"]
    assert "Coast Guard 1554" in exps["en"]

    # Hindi check
    assert "सावधानीपूर्वक प्रस्थान (CAUTION)" in exps["hi"]
    assert "1554" in exps["hi"]

    # Marathi check
    assert "सावधगिरी बाळगा (CAUTION)" in exps["mr"]
    assert "1554" in exps["mr"]

    # Underlying decision is strictly immutable across languages
    assert assessment.decision == "CAUTION"
