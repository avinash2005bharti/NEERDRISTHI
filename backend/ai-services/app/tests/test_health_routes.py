from starlette.testclient import TestClient
from app.main import app


def test_public_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orca-agent-core"
        assert "providers" in data
        assert data["providers"]["mongodb"] in ["connected", "unconfigured_or_unreachable"]


def test_internal_execution_endpoint_with_valid_secret():
    with TestClient(app) as client:
        payload = {
            "query": "Is it safe to depart Chennai harbor?",
            "location": {"name": "Chennai Harbor", "latitude": 13.08, "longitude": 80.27},
            "userProfile": {"role": "fisherman", "vesselClass": "motorized_fiberglass", "language": "en"}
        }
        # In default local dev mode with empty secret, header is accepted
        response = client.post(
            "/internal/v1/orca/execute",
            json=payload,
            headers={"x-internal-service-secret": ""}
        )
        assert response.status_code == 200
        data = response.json()
        assert "requestId" in data
        assert data["recommendation"] in ["GO", "GO_WITH_CAUTION", "NO_GO", "INSUFFICIENT_DATA"]
