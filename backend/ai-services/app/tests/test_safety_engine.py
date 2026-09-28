import pytest
from app.safety.engine import SafetyRiskEngine
from app.safety.policy import load_safety_policy


@pytest.fixture
def engine():
    return SafetyRiskEngine()


def test_missing_weather_telemetry_defaults_to_insufficient_data(engine):
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=None,
        marine_data=None,
        geospatial_data=None,
        data_availability={"weather": "unavailable", "marine": "unavailable"},
    )
    assert result.recommendation == "INSUFFICIENT_DATA"
    assert result.risk_level == "UNKNOWN"
    assert len(result.missing_data) > 0
    assert result.confidence_score <= 30


def test_severe_weather_alert_triggers_no_go(engine):
    weather_data = {
        "wave_height_meters": 1.0,
        "wind_speed_mps": 5.0,
        "warning_flag": "Cyclonic Storm Warning Bulletin #3",
    }
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=weather_data,
        marine_data=None,
        geospatial_data=None,
        data_availability={"weather": "available"},
    )
    assert result.recommendation == "NO_GO"
    assert result.risk_level == "CRITICAL"
    assert any("Severe Weather Alert" in r for r in result.triggered_rules)


def test_wave_height_exceedance_triggers_no_go(engine):
    weather_data = {
        "wave_height_meters": 2.8,
        "wind_speed_mps": 6.0,
        "observed_at": "2026-09-24T12:00:00Z",
    }
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=weather_data,
        marine_data=None,
        geospatial_data=None,
        data_availability={"weather": "available"},
    )
    assert result.recommendation == "NO_GO"
    assert result.risk_level == "HIGH"
    assert any("wave height" in r.lower() for r in result.triggered_rules)


def test_wave_height_cautionary_margin(engine):
    weather_data = {
        "wave_height_meters": 1.7,
        "wind_speed_mps": 6.0,
        "observed_at": "2026-09-24T12:00:00Z",
    }
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=weather_data,
        marine_data=None,
        geospatial_data=None,
        data_availability={"weather": "available"},
    )
    assert result.recommendation == "GO_WITH_CAUTION"
    assert result.risk_level == "MODERATE"


def test_restricted_zone_intersection_triggers_no_go(engine):
    weather_data = {
        "wave_height_meters": 0.8,
        "wind_speed_mps": 4.0,
    }
    geospatial_data = {
        "restricted_zone_intersections": [{"name": "Naval Firing Range Alpha"}]
    }
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=weather_data,
        marine_data=None,
        geospatial_data=geospatial_data,
        data_availability={"weather": "available"},
    )
    assert result.recommendation == "NO_GO"
    assert result.risk_level == "CRITICAL"
    assert any("restricted" in r.lower() for r in result.triggered_rules)


def test_favorable_conditions_with_live_telemetry_permits_go(engine):
    weather_data = {
        "wave_height_meters": 0.7,
        "wind_speed_mps": 4.5,
        "observed_at": "2026-09-24T12:00:00Z",
    }
    result = engine.evaluate(
        vessel_class="motorized_fiberglass",
        weather_data=weather_data,
        marine_data=None,
        geospatial_data={"restricted_zone_intersections": []},
        data_availability={"weather": "available"},
    )
    assert result.recommendation == "GO"
    assert result.risk_level == "LOW"
    assert result.risk_score <= 25
