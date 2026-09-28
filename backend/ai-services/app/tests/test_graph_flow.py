import pytest
from app.schemas.contracts import OrcaQueryRequest
from app.services.orchestrator import orchestrator


@pytest.mark.asyncio
async def test_end_to_end_query_with_empty_credentials(monkeypatch):
    """
    CRITICAL INVARIANT TEST:
    When external API credentials are blank, /api/v1/orca/query workflow must:
    1. Complete without throwing unhandled exceptions.
    2. Correctly report data availability as 'unavailable'.
    3. Return deterministic recommendation 'INSUFFICIENT_DATA' (never 'GO').
    4. Provide evidence indicating which telemetries are missing.
    """
    from app.integrations.weather_adapter import weather_adapter
    from app.integrations.incois_adapter import incois_adapter
    from app.integrations.tide_adapter import tide_adapter

    monkeypatch.setattr(weather_adapter, "base_url", "")
    monkeypatch.setattr(weather_adapter, "forecast_endpoint", "")
    monkeypatch.setattr(incois_adapter, "base_url", "")
    monkeypatch.setattr(incois_adapter, "pfz_endpoint", "")
    monkeypatch.setattr(tide_adapter, "base_url", "")
    monkeypatch.setattr(tide_adapter, "tide_endpoint", "")
    monkeypatch.setattr(tide_adapter, "marine_base_url", "")

    request = OrcaQueryRequest(
        query="Is it safe for my fiberglass boat to venture out from Visakhapatnam to catch tuna today?",
        location={"latitude": 17.68, "longitude": 83.21},
        userProfile={"role": "fisherman", "vesselClass": "motorized_fiberglass", "language": "en"},
    )

    response = await orchestrator.execute_query(request, request_id="test-req-001")

    assert response.requestId == "test-req-001"
    assert response.recommendation == "INSUFFICIENT_DATA"
    assert response.dataAvailability.weather == "unavailable"
    assert response.dataAvailability.marine == "unavailable"
    assert "Weather" in response.safety.missingData[0]
    assert response.confidenceScore <= 30
    assert len(response.trace.agentStatuses) >= 4


@pytest.mark.asyncio
async def test_end_to_end_query_with_live_telemetry():
    """
    Live telemetry integration test:
    When default Open-Meteo endpoints are reachable, workflow evaluates live weather
    and returns a recommendation with populated agent trace.
    """
    request = OrcaQueryRequest(
        query="Is it safe for my fiberglass boat to venture out from Visakhapatnam to catch tuna today?",
        location={"latitude": 17.68, "longitude": 83.21},
        userProfile={"role": "fisherman", "vesselClass": "motorized_fiberglass", "language": "en"},
    )

    response = await orchestrator.execute_query(request, request_id="test-req-live-001")

    assert response.requestId == "test-req-live-001"
    assert response.recommendation in ["GO", "GO_WITH_CAUTION", "NO_GO"]
    assert response.dataAvailability.weather in ["available", "stale"]
    assert len(response.trace.agentStatuses) >= 4
