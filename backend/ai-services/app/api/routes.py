from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ..schemas.contracts import OrcaQueryRequest, OrcaQueryResponse
from ..schemas.adapters import WeatherObservation, DataUnavailableResult
from ..services.orchestrator import orchestrator
from ..services.marine_alerts import marine_alerts_provider
from ..repositories.audit_repository import audit_repository
from ..integrations.incois_adapter import incois_adapter
from ..integrations.weather_adapter import weather_adapter
from ..integrations.tide_adapter import tide_adapter
from ..memory.qdrant_service import qdrant_service
from ..memory.ltm_vector import ltm_service
from ..services.groq_client import groq_client
from ..cache.valkey_client import cache_client
from ..gis.spatial_engine import spatial_engine
from ..sandbox.runner import sandbox_runner, SandboxExecutionRequest, SandboxExecutionResult
from ..safety.engine import safety_engine
from .dependencies import verify_internal_service_secret
from ..observability.logger import logger

# Import open-data providers, registry, and safety evaluator
from ..adapters import (
    open_meteo_weather_provider,
    open_meteo_marine_provider,
    nominatim_geocoder_provider,
    local_tide_dataset_provider,
    local_satellite_demo_provider,
    pfz_estimator,
    gdacs_alert_provider,
)
from ..providers.registry import provider_registry
from ..services.safety_evaluator import safety_evaluator
from ..schemas.normalized import (
    WeatherForecast,
    MarineForecast,
    TideObservation as NormalizedTideObservation,
    SatelliteObservation,
    SafetyAssessment as NormalizedSafetyAssessment,
    MarineAlert,
    PFZSuitabilityEstimate,
)
from ..core.config import settings
from ..providers.gateway import marine_data_gateway

router = APIRouter()


# ─── Detailed Health Diagnostic ───────────────────────────────────────────────

@router.get("/health/detail", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check endpoint reporting Python AI & GIS provider configuration.
    For ultra-lightweight orchestrator liveness checks, use root GET /health.
    Note: Primary application database (MongoDB) is managed exclusively by Node.js.
    """
    valkey_ok = await cache_client.ping()
    return {
        "status": "healthy",
        "service": "orca-agent-core",
        "role": "AI / LangGraph Multi-Agent & Spatial Intelligence Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": {
            "langgraph": "ready",
            "spatial_engine_gis": "ready (GeoPandas/Shapely)" if spatial_engine.available else "algorithmic",
            "sandbox_service": "ready",
            "groq_llm": "configured" if groq_client.is_configured() else "unconfigured",
            "qdrant_cloud_ltm": "configured" if qdrant_service.is_configured() else "unconfigured",
            "incois": "configured" if incois_adapter.is_configured() else "open_meteo_fallback",
            "weather": "configured" if weather_adapter.is_configured() else "unconfigured",
            "tide": "configured" if tide_adapter.is_configured() else "open_meteo_marine_fallback",
            "valkey_cache": "connected" if valkey_ok else "unavailable",
            "mongodb": "unconfigured_or_unreachable",  # Explicitly not connected from Python
        },
        "components": {
            "langgraph": "ready",
            "spatial_engine_gis": "ready (GeoPandas/Shapely)" if spatial_engine.available else "algorithmic",
            "sandbox_service": "ready",
            "groq_llm": "configured" if groq_client.is_configured() else "unconfigured",
            "qdrant_cloud_ltm": "configured" if qdrant_service.is_configured() else "unconfigured",
            "incois": "configured" if incois_adapter.is_configured() else "open_meteo_fallback",
            "weather": "configured" if weather_adapter.is_configured() else "unconfigured",
            "tide": "configured" if tide_adapter.is_configured() else "open_meteo_marine_fallback",
            "valkey_cache": "connected" if valkey_ok else "unavailable",
        },
    }


# ─── Internal AI Service Contract (Section 13) ────────────────────────────────

@router.post(
    "/internal/ai/chat",
    response_model=OrcaQueryResponse,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
@router.post(
    "/internal/v1/orca/execute",
    response_model=OrcaQueryResponse,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
async def execute_agent_chat(
    request: OrcaQueryRequest,
    x_request_id: Optional[str] = Header(default=None, alias="x-request-id"),
):
    """
    Primary AI multi-agent orchestration endpoint called by Node.js API Gateway.
    Processes query with LangGraph workflow, retrieves LTM from Vector DB,
    and returns grounded response with deterministic safety assessment.
    """
    request_id = x_request_id or str(uuid4())
    logger.info(f"Executing AI workflow for requestId: {request_id}")

    try:
        response = await orchestrator.execute_query(request, request_id)
        return response
    except Exception as e:
        logger.error(f"Fatal error executing query {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.post(
    "/internal/ai/analyze",
    response_model=OrcaQueryResponse,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
async def execute_marine_analysis(
    request: OrcaQueryRequest,
    x_request_id: Optional[str] = Header(default=None, alias="x-request-id"),
):
    """
    Dedicated marine safety and PFZ analysis execution endpoint.
    Forces intent to 'safety_check' or 'find_pfz'.
    """
    request_id = x_request_id or str(uuid4())
    if not request.intent:
        request.intent = "safety_check"
    return await orchestrator.execute_query(request, request_id)


@router.post(
    "/internal/ai/marine-query",
    response_model=OrcaQueryResponse,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
async def execute_marine_query(
    request: OrcaQueryRequest,
    x_request_id: Optional[str] = Header(default=None, alias="x-request-id"),
):
    """Direct marine status query processor."""
    request_id = x_request_id or str(uuid4())
    if not request.intent:
        request.intent = "marine_status"
    return await orchestrator.execute_query(request, request_id)


class RouteAnalysisRequest(BaseModel):
    waypoints: List[Tuple[float, float]] = Field(..., description="List of [lon, lat] tuples")
    vessel_class: Optional[str] = Field(default="motorized_fiberglass")
    buffer_km: float = Field(default=2.0)


@router.post(
    "/internal/ai/route-analysis",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
async def execute_route_analysis(request: RouteAnalysisRequest):
    """
    Deterministic GeoPandas route safety and hazard buffer analysis.
    Checks waypoints against designated restricted zones, EEZ boundaries, and computes navigational distance.
    """
    if len(request.waypoints) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Route requires at least 2 waypoints."
        )

    # 1. Total route distance and legs
    total_km = 0.0
    legs = []
    for i in range(len(request.waypoints) - 1):
        pt1 = request.waypoints[i]
        pt2 = request.waypoints[i + 1]
        leg_dist = spatial_engine.haversine_distance_km(pt1, pt2)
        bearing = spatial_engine.calculate_bearing_deg(pt1, pt2)
        total_km += leg_dist
        legs.append({
            "leg_index": i + 1,
            "from_coord": pt1,
            "to_coord": pt2,
            "distance_km": round(leg_dist, 2),
            "bearing_deg": round(bearing, 1),
        })

    # 2. GeoPandas restricted zone intersection
    restricted_hits = spatial_engine.check_route_intersections(
        request.waypoints, buffer_km=request.buffer_km
    )

    is_safe = len(restricted_hits) == 0
    return {
        "status": "completed",
        "route_summary": {
            "total_distance_km": round(total_km, 2),
            "waypoint_count": len(request.waypoints),
            "leg_count": len(legs),
            "buffer_km": request.buffer_km,
        },
        "legs": legs,
        "hazard_intersections": restricted_hits,
        "is_safe": is_safe,
        "recommendation": "GO" if is_safe else "NO_GO",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class RiskAnalysisRequest(BaseModel):
    vessel_class: str
    latitude: float
    longitude: float


@router.post(
    "/internal/ai/risk-analysis",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["AI Services"],
)
async def execute_risk_analysis(request: RiskAnalysisRequest):
    """
    Direct deterministic risk engine evaluation for a vessel class at coordinates.
    """
    # Fetch real live weather and waves
    wx_result = await weather_adapter.fetch_weather_and_waves(
        latitude=request.latitude, longitude=request.longitude
    )
    weather_dict = wx_result.model_dump() if hasattr(wx_result, "model_dump") else None

    # Check GIS restricted zones
    gis_hits = spatial_engine.check_point_intersections(request.longitude, request.latitude)

    assessment = safety_engine.evaluate(
        vessel_class=request.vessel_class,
        weather_data=weather_dict,
        marine_data=None,
        geospatial_data={"restricted_zone_intersections": gis_hits},
        data_availability={"weather": "available" if weather_dict else "unavailable"},
        evidence_list=[],
    )

    return {
        "recommendation": assessment.recommendation,
        "risk_level": assessment.risk_level,
        "risk_score": assessment.risk_score,
        "confidence_score": assessment.confidence_score,
        "triggered_rules": assessment.triggered_rules,
        "missing_data": assessment.missing_data,
        "required_next_action": assessment.required_next_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Isolated Sandbox Execution (Section 17) ──────────────────────────────────

@router.post(
    "/internal/ai/sandbox/execute",
    response_model=SandboxExecutionResult,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Sandbox"],
)
async def execute_isolated_sandbox(request: SandboxExecutionRequest):
    """
    Executes Python scripts, CSV data analysis, or marine GIS calculations inside an ephemeral,
    restricted sandbox process with strict resource bounds, filesystem isolation, and timeout limits.
    """
    logger.info("Dispatching isolated code execution to SandboxRunner")
    result = await sandbox_runner.execute(request)
    return result


@router.get(
    "/internal/v1/orca/request/{request_id}",
    response_model=OrcaQueryResponse,
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Agent Core Internal"],
)
async def get_request_status(request_id: str):
    """Fetch cached status of a recent request from in-memory trace cache."""
    cached_query = await audit_repository.get_query_result(request_id)
    if not cached_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )
    return cached_query


# ─── Direct Scientific Marine Telemetry Endpoints ─────────────────────────────

@router.get(
    "/internal/ai/marine/weather",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
@router.get(
    "/internal/v1/marine/weather",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
async def get_weather_data(
    latitude: float = Query(..., description="Latitude in decimal degrees", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude in decimal degrees", ge=-180, le=180),
):
    """
    Fetch current atmospheric weather and sea-state data for a location.
    Provider: Open-Meteo (atmospheric + marine). Cached in Valkey.
    """
    result = await weather_adapter.fetch_weather_and_waves(latitude=latitude, longitude=longitude)
    if isinstance(result, WeatherObservation):
        return {
            "status": "available",
            "provider": result.provider,
            "data": result.model_dump(),
            "retrieved_at": result.retrieved_at,
        }
    elif hasattr(result, "wind_speed_mps"):
        return {
            "status": "available",
            "provider": getattr(result, "provider", "Open-Meteo"),
            "data": result.model_dump() if hasattr(result, "model_dump") else dict(result),
            "retrieved_at": getattr(result, "retrieved_at", datetime.now(timezone.utc).isoformat()),
        }
    else:
        return {
            "status": "unavailable",
            "reason": getattr(result, "reason", "Weather data unavailable"),
            "provider": getattr(result, "provider_name", "Unknown"),
        }


@router.get(
    "/internal/ai/marine/ocean",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
@router.get(
    "/internal/v1/marine/ocean",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
async def get_ocean_state(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    """
    Fetch ocean state: SST, tide, and PFZ telemetry for a location.
    """
    now_str = datetime.now(timezone.utc).isoformat()

    pfz_result = await incois_adapter.fetch_pfz(latitude=latitude, longitude=longitude)
    pfz_data = None
    if isinstance(pfz_result, list) and pfz_result:
        pfz_data = [r.model_dump() for r in pfz_result]

    tide_result = await tide_adapter.fetch_tide(latitude=latitude, longitude=longitude)
    tide_data = None
    if hasattr(tide_result, "tide_height_meters"):
        tide_data = tide_result.model_dump()

    return {
        "status": "available",
        "retrieved_at": now_str,
        "location": {"latitude": latitude, "longitude": longitude},
        "pfz_records": pfz_data,
        "tide": tide_data,
        "pfz_status": "available" if pfz_data else "unavailable",
        "tide_status": "available" if tide_data else "unavailable",
    }


@router.get(
    "/internal/ai/marine/pfz",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
@router.get(
    "/internal/v1/marine/pfz",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
async def get_pfz_data(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    """
    Fetch Potential Fishing Zone (PFZ) data.
    Primary: INCOIS official bulletin (if configured).
    Fallback: Open-Meteo Marine SST proxy.
    """
    result = await incois_adapter.fetch_pfz(latitude=latitude, longitude=longitude)
    now_str = datetime.now(timezone.utc).isoformat()

    if isinstance(result, list) and result:
        return {
            "status": "available",
            "provider": result[0].provider,
            "retrieved_at": now_str,
            "records": [r.model_dump() for r in result],
            "count": len(result),
        }
    return {
        "status": "unavailable",
        "reason": result.reason if hasattr(result, "reason") else "PFZ data unavailable",
        "retrieved_at": now_str,
    }


@router.get(
    "/internal/ai/marine/alerts",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
@router.get(
    "/internal/v1/marine/alerts",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
async def get_marine_alerts(
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
):
    """
    Fetch real marine safety hazard alerts.
    """
    if latitude is not None and longitude is not None:
        result = await marine_alerts_provider.fetch_alerts_for_location(latitude, longitude)
    else:
        result = await marine_alerts_provider.fetch_regional_alerts()
    return result


@router.get(
    "/internal/ai/marine/zones",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
@router.get(
    "/internal/v1/marine/zones",
    dependencies=[Depends(verify_internal_service_secret)],
    tags=["Marine Data"],
)
async def get_marine_zones(
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(150.0, description="Search radius in kilometers"),
):
    """
    Fetch GeoJSON marine zones (restricted, naval ranges, protected reefs)
    computed via GeoPandas SpatialEngine for maritime map rendering.
    """
    geojson = spatial_engine.generate_zones_geojson(
        center_lon=longitude,
        center_lat=latitude,
        radius_km=radius_km,
    )
    return geojson


# ─── Public Open Data & Reasoning Endpoints (SIH26176) ────────────────────────

@router.get("/providers", tags=["Open Data Providers"])
async def list_providers():
    """List all registered external data providers, their base URLs, license, and status."""
    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": provider_registry.list_providers(),
    }


@router.get("/weather/forecast", response_model=Dict[str, Any], tags=["Weather & Sea State"])
async def get_weather_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180"),
    forecast_days: int = Query(3, ge=1, le=14, description="Forecast horizon in days (1-14)"),
):
    """
    Fetch multi-variable weather forecast from primary open-data provider (Open-Meteo).
    Variables: temperature_2m, relative_humidity_2m, precipitation, rain, weather_code,
               cloud_cover, surface_pressure, wind_speed_10m, wind_direction_10m,
               wind_gusts_10m, visibility.
    """
    result = await provider_registry.fetch_weather_forecast(
        latitude=latitude, longitude=longitude, forecast_days=forecast_days
    )
    if isinstance(result, dict) and result.get("status") == "DATA_UNAVAILABLE":
        return {
            "status": "unavailable",
            "data_status": "DATA_UNAVAILABLE",
            "category": "weather",
            "reason": result.get("reason", "Weather data unavailable"),
            "data": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attribution": {"source": "Open-Meteo", "url": "https://open-meteo.com"},
        }
    data_dict = result.model_dump() if hasattr(result, "model_dump") else result
    return {
        "status": "success",
        "data_status": getattr(result, "data_status", "forecast"),
        "provider": getattr(result, "provider", "Open-Meteo Weather API"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data_dict,
        "attribution": {
            "source": "Open-Meteo",
            "url": "https://open-meteo.com",
            "license": "CC BY 4.0",
        },
    }


@router.get("/marine/forecast", response_model=Dict[str, Any], tags=["Marine Data"])
async def get_marine_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    forecast_days: int = Query(3, ge=1, le=8),
):
    """
    Fetch marine wave and ocean current forecast from Open-Meteo Marine API.
    Variables: wave_height, wave_direction, wave_period, wind_wave_height,
               swell_wave_height, ocean_current_velocity, ocean_current_direction, sea_level.
    """
    result = await provider_registry.fetch_marine_forecast(
        latitude=latitude, longitude=longitude, forecast_days=forecast_days
    )
    if isinstance(result, dict) and result.get("status") == "DATA_UNAVAILABLE":
        return {
            "status": "unavailable",
            "data_status": "DATA_UNAVAILABLE",
            "category": "marine",
            "reason": result.get("reason", "Marine data unavailable"),
            "data": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attribution": {"source": "Open-Meteo Marine", "url": "https://marine-api.open-meteo.com"},
        }
    data_dict = result.model_dump() if hasattr(result, "model_dump") else result
    return {
        "status": "success",
        "data_status": getattr(result, "data_status", "forecast"),
        "provider": getattr(result, "provider", "Open-Meteo Marine API"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data_dict,
        "attribution": {
            "source": "Open-Meteo Marine API",
            "url": "https://marine-api.open-meteo.com",
            "license": "CC BY 4.0",
        },
    }


@router.get("/tide", response_model=Dict[str, Any], tags=["Marine Data"])
async def get_tide_data(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    station_id: Optional[str] = Query(None, description="Optional coastal tide station identifier"),
):
    """
    Fetch tidal water-level observation or prediction.
    Cascades through:
    1. Official tide provider (if credentials configured)
    2. NOAA CO-OPS (if supported station)
    3. FES / TPXO (if endpoint configured)
    4. Local coastal tide-station dataset (India coastline)
    5. Clearly labelled water-level fallback
    If no source available, returns status='DATA_UNAVAILABLE'.
    Never silently substitutes wave height for tide height.
    """
    result = await provider_registry.fetch_tide(latitude=latitude, longitude=longitude, station_id=station_id)
    if isinstance(result, dict) and result.get("status") == "DATA_UNAVAILABLE":
        return {
            "status": "DATA_UNAVAILABLE",
            "category": "tide",
            "data_status": "DATA_UNAVAILABLE",
            "reason": result.get("reason", "No configured tide provider for this location"),
            "data": None,
            "provider": "none",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    data_dict = result.model_dump() if hasattr(result, "model_dump") else result
    return {
        "status": "success",
        "data_status": getattr(result, "data_status", "prediction"),
        "provider": getattr(result, "provider", "TideProvider"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data_dict,
        "attribution": {
            "source": getattr(result, "provider", "Tide Station Network"),
            "url": getattr(result, "source_url", "https://incois.gov.in"),
            "notice": "Tidal prediction relative to Chart Datum (CD).",
        },
    }


@router.get("/satellite/observations", response_model=Dict[str, Any], tags=["Satellite & Ocean Color"])
async def get_satellite_observations(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Fetch satellite ocean-color and sea-surface temperature observations.
    In demo mode, loads from verified local open-data benchmarks with explicit demo metadata.
    """
    obs_list = await provider_registry.fetch_satellite(latitude=latitude, longitude=longitude)
    if isinstance(obs_list, dict) and obs_list.get("status") == "DATA_UNAVAILABLE":
        return {
            "status": "unavailable",
            "data_status": "DATA_UNAVAILABLE",
            "reason": obs_list.get("reason", "Satellite data unavailable"),
            "records": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    records = [r.model_dump() if hasattr(r, "model_dump") else r for r in (obs_list or [])]
    return {
        "status": "success",
        "count": len(records),
        "data_status": records[0].get("data_status") if records else "unknown",
        "records": records,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": {
            "source": "Copernicus Marine Service / NASA Earthdata (Demo Benchmark)",
            "notice": "Satellite data clearly distinguished as demo / research dataset.",
        },
    }


@router.get("/alerts", response_model=Dict[str, Any], tags=["Alerts & Warnings"])
async def get_alerts(
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
):
    """
    Fetch active cyclone and severe marine weather warnings.
    Aggregates from GDACS, IMD (if configured), NOAA NHC, and computed physical risk signals.
    """
    alerts = await provider_registry.fetch_alerts(latitude=latitude, longitude=longitude)
    records = [a.model_dump() if hasattr(a, "model_dump") else a for a in alerts]
    return {
        "status": "success",
        "count": len(records),
        "alerts": records,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": {
            "source": "GDACS / Official Meteorological Feeds",
            "url": "https://www.gdacs.org",
        },
    }


@router.get("/fishing-zone/estimate", response_model=Dict[str, Any], tags=["Marine Data"])
async def get_fishing_zone_estimate(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Compute experimental Potential Fishing Zone (PFZ) suitability estimate.
    Combines SST, chlorophyll-a, thermal gradient, bathymetry, and weather stability.
    Clearly labeled 'experimental fishing-zone suitability' / 'research estimate'.
    Does NOT claim to be an official INCOIS PFZ bulletin.
    """
    wx_data = await provider_registry.fetch_weather_forecast(latitude, longitude)
    wx_dict = wx_data.model_dump() if hasattr(wx_data, "model_dump") else None

    estimate = await pfz_estimator.estimate_suitability(
        latitude=latitude,
        longitude=longitude,
        weather_data=wx_dict,
    )
    return {
        "status": "success",
        "data": estimate.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class SafetyAssessRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    vessel_class: Optional[str] = Field(default="motorized_fiberglass")
    language: Optional[str] = Field(default="en")


@router.post("/safety/assess", response_model=Dict[str, Any], tags=["Safety Engine"])
async def assess_safety(request: SafetyAssessRequest):
    """
    Evaluate deterministic maritime safety rules and produce explainable multilingual guidance.
    Hierarchy:
    1. Cyclone & Severe Weather Warnings (Immediate NO_GO).
    2. Critical Data Gap Enforcement (Never returns GO on missing data).
    3. Vessel Limits (Wave height, wave period, wind speed, gusts).
    4. Visibility & Precipitation.
    5. Tidal water-level context (if available).
    6. Multilingual explanations (English, Hindi, Marathi).
    """
    # 1. Fetch live telemetry from provider registry
    wx_data = await provider_registry.fetch_weather_forecast(request.latitude, request.longitude)
    mar_data = await provider_registry.fetch_marine_forecast(request.latitude, request.longitude)
    tide_data = await provider_registry.fetch_tide(request.latitude, request.longitude)
    alerts = await provider_registry.fetch_alerts(request.latitude, request.longitude)

    wx_dict = wx_data.model_dump() if hasattr(wx_data, "model_dump") else wx_data
    mar_dict = mar_data.model_dump() if hasattr(mar_data, "model_dump") else mar_data
    tide_dict = tide_data.model_dump() if hasattr(tide_data, "model_dump") else tide_data
    alerts_list = [a.model_dump() if hasattr(a, "model_dump") else a for a in alerts]

    # 2. Run deterministic safety evaluation
    assessment = safety_evaluator.evaluate_safety(
        latitude=request.latitude,
        longitude=request.longitude,
        vessel_class=request.vessel_class or "motorized_fiberglass",
        weather_data=wx_dict if isinstance(wx_dict, dict) and wx_dict.get("status") != "DATA_UNAVAILABLE" else None,
        marine_data=mar_dict if isinstance(mar_dict, dict) and mar_dict.get("status") != "DATA_UNAVAILABLE" else None,
        tide_data=tide_dict if isinstance(tide_dict, dict) and tide_dict.get("status") != "DATA_UNAVAILABLE" else None,
        alerts=alerts_list,
    )

    return {
        "status": "success",
        "assessment": assessment.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/data-sources", tags=["Documentation & Licensing"])
async def get_data_sources():
    """
    Return comprehensive documentation of all integrated open data providers,
    licensing, update frequency, and production suitability.
    """
    return {
        "system": "ORCA Marine Intelligence (SIH26176)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_sources": [
            {
                "name": "Open-Meteo Weather API",
                "category": "weather",
                "type": "open_data",
                "base_url": "https://api.open-meteo.com",
                "endpoint": "GET /v1/forecast",
                "auth_required": False,
                "rate_limits": "10,000 requests/day, 10/second (free tier)",
                "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                "coverage": "Global (0.1° / ~11km ECMWF IFS & DWD ICON)",
                "update_frequency": "Hourly",
                "status": "forecast",
                "production_suitability": "Production ready (Commercial API available from Open-Meteo GmbH)",
            },
            {
                "name": "Open-Meteo Marine API",
                "category": "marine",
                "type": "open_data",
                "base_url": "https://marine-api.open-meteo.com",
                "endpoint": "GET /v1/marine",
                "auth_required": False,
                "rate_limits": "10,000 requests/day, 10/second (free tier)",
                "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                "coverage": "Global oceans (5km coastal / 25km oceanic)",
                "update_frequency": "Hourly (ECMWF WAM & NOAA WaveWatch III)",
                "status": "forecast",
                "production_suitability": "Production ready",
            },
            {
                "name": "Nominatim / OpenStreetMap",
                "category": "geocoding",
                "type": "open_data",
                "base_url": "https://nominatim.openstreetmap.org",
                "endpoint": "GET /search, GET /reverse",
                "auth_required": False,
                "rate_limits": "1 request/second (public instance); unlimited on self-hosted",
                "license": "Open Database License (ODbL) by OpenStreetMap Foundation",
                "coverage": "Global coastal and inland points of interest",
                "update_frequency": "Continuous",
                "status": "reference",
                "production_suitability": "Self-host via Docker for high-volume production",
            },
            {
                "name": "Local Coastal Tide Station Dataset",
                "category": "tide",
                "type": "self_hostable_dataset",
                "base_url": "local://data/tide",
                "auth_required": False,
                "rate_limits": "Unlimited (in-memory / local storage)",
                "license": "Open Data Commons / Port Trust Published Constants",
                "coverage": "Major Indian ports (Mumbai, Chennai, Kochi, Mormugao, Kandla, Vizag)",
                "update_frequency": "Astronomical Harmonic Constants",
                "status": "prediction",
                "production_suitability": "Production ready for coastal decision support",
            },
            {
                "name": "NOAA CO-OPS Tides and Currents",
                "category": "tide",
                "type": "open_data",
                "base_url": "https://api.tidesandcurrents.noaa.gov",
                "auth_required": False,
                "rate_limits": "Public open access",
                "license": "U.S. Public Domain",
                "coverage": "U.S. & International Partner Tide Stations",
                "update_frequency": "Real-time & Astronomical Predictions",
                "status": "prediction / observation",
                "production_suitability": "Production ready",
            },
            {
                "name": "GDACS Disaster Alerts",
                "category": "alerts",
                "type": "open_data",
                "base_url": "https://www.gdacs.org",
                "endpoint": "GET /xml/rss.xml",
                "auth_required": False,
                "rate_limits": "Public RSS/GeoJSON feed",
                "license": "United Nations OCHA / European Commission Open Data",
                "coverage": "Global tropical cyclone and severe disaster alerts",
                "update_frequency": "Every 15-30 minutes during active events",
                "status": "official_alert",
                "production_suitability": "Production ready",
            },
            {
                "name": "Copernicus Marine Service (CMEMS)",
                "category": "marine / satellite",
                "type": "open_data_registration_required",
                "base_url": "https://cq-cmems.copernicus.eu",
                "auth_required": True,
                "rate_limits": "Governed by CMEMS User Account",
                "license": "E.U. Copernicus Marine Open License",
                "coverage": "Global L4 SST & Ocean Colour (1km resolution)",
                "update_frequency": "Daily",
                "status": "observation / near_real_time",
                "production_suitability": "Production ready post-registration",
            },
        ],
    }


@router.get("/demo/status", tags=["Documentation & Licensing"])
async def get_demo_status():
    """Return status of demo mode, local benchmark datasets, and active configurations."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "environment": settings.APP_ENV,
        "configured_providers": {
            "weather": settings.WEATHER_PROVIDER,
            "marine": settings.MARINE_PROVIDER,
            "geocoder": settings.GEOCODER_PROVIDER,
            "tide": settings.TIDE_PROVIDER,
            "satellite": settings.SATELLITE_PROVIDER,
            "alerts": settings.ALERT_PROVIDER,
        },
        "local_datasets": {
            "tide_stations": True,
            "satellite_demo_sst_chlorophyll": True,
        },
        "live_credentials_status": {
            "groq_configured": settings.is_groq_configured,
            "qdrant_configured": settings.is_qdrant_configured,
            "incois_configured": settings.is_incois_configured,
            "copernicus_configured": bool(settings.SATELLITE_API_KEY),
        },
        "guidance": (
            "ORCA is operating in legally compliant open-data demo mode. "
            "Weather, marine waves, geocoding, and GDACS alerts use live open APIs requiring no key. "
            "Tide and satellite data utilize attributed local benchmark datasets. "
            "To connect registered providers (e.g. Copernicus, IMD), update your .env file."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Marine Data Gateway Endpoints (SIH26176 Production Layer) ────────────────

@router.get("/api/marine/weather", tags=["Marine Data Gateway"])
async def api_marine_weather(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)"),
    date: Optional[str] = Query(None, description="Target forecast date (YYYY-MM-DD)"),
    start_time: Optional[str] = Query(None, description="Optional start time"),
    end_time: Optional[str] = Query(None, description="Optional end time"),
):
    """
    Atmospheric weather forecast from centralized Marine Data Gateway.
    Primary: Open-Meteo Weather API.
    Automatic Fallback: MET Norway (Locationforecast/2.0).
    """
    return await marine_data_gateway.get_weather_forecast(latitude, longitude, date)


@router.get("/api/marine/conditions", tags=["Marine Data Gateway"])
async def api_marine_conditions(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
    date: Optional[str] = Query(None, description="Target forecast date (YYYY-MM-DD)"),
    start_time: Optional[str] = Query(None, description="Optional start time"),
    end_time: Optional[str] = Query(None, description="Optional end time"),
):
    """
    Ocean wave and sea-state conditions from centralized Marine Data Gateway.
    Variables: significant wave height, dominant wave period, wave direction, swell, SST, currents.
    Primary: Open-Meteo Marine. Enriched with INCOIS ERDDAP & Copernicus where available.
    """
    return await marine_data_gateway.get_marine_conditions(latitude, longitude, date)


@router.get("/api/marine/ocean", tags=["Marine Data Gateway"])
async def api_marine_ocean(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
    date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
):
    """
    Ocean state, biology, chlorophyll-a, and sea-surface temperature from INCOIS ERDDAP & Copernicus.
    """
    return await marine_data_gateway.get_ocean_conditions(latitude, longitude, date)


@router.get("/api/marine/sst", tags=["Marine Data Gateway"])
async def api_marine_sst(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
):
    """
    Sea Surface Temperature (SST) in Celsius from INCOIS ERDDAP with Open-Meteo Marine fallback.
    """
    sst = await marine_data_gateway.get_sst(latitude, longitude)
    return {
        "status": "success" if sst is not None else "unavailable",
        "latitude": latitude,
        "longitude": longitude,
        "sea_surface_temperature": sst,
        "unit": "Celsius",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/marine/chlorophyll", tags=["Marine Data Gateway"])
async def api_marine_chlorophyll(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
):
    """
    Ocean chlorophyll-a concentration in mg/m³ from INCOIS ERDDAP satellite ocean color data.
    """
    chl = await marine_data_gateway.get_chlorophyll(latitude, longitude)
    return {
        "status": "success" if chl is not None else "unavailable",
        "latitude": latitude,
        "longitude": longitude,
        "chlorophyll": chl,
        "unit": "mg/m³",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/marine/tide", tags=["Marine Data Gateway"])
async def api_marine_tide(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
    date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
):
    """
    Water level and tidal elevation from Open-Meteo Marine modeled sea level (with optional WorldTides).
    Explicitly tags whether prediction is hydrographic tide table or modeled open-ocean MSL elevation.
    """
    return await marine_data_gateway.get_tide(latitude, longitude, date)


@router.get("/api/marine/fishing-zones", tags=["Marine Data Gateway"])
async def api_marine_fishing_zones(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
):
    """
    Potential Fishing Zones (PFZ) advisory.
    Uses Official INCOIS PFZ if configured; otherwise provides AI-derived candidate fishing zones
    calculated from SST thermal fronts, chlorophyll concentration, and ocean currents.
    """
    return await marine_data_gateway.get_fishing_zones(latitude, longitude)


@router.get("/api/marine/providers/status", tags=["Marine Data Gateway"])
async def api_marine_providers_status():
    """
    Operational status of all integrated marine, weather, ocean, and geospatial data providers.
    Complies with SIH26176 Section 19.
    """
    return await marine_data_gateway.get_providers_status()


@router.get("/api/marine/health", tags=["Marine Data Gateway"])
async def api_marine_health():
    """
    Health check endpoint for the Marine Data Gateway.
    """
    status = await marine_data_gateway.get_providers_status()
    all_healthy = status["open_meteo"]["status"] == "available" and status["open_meteo_marine"]["status"] == "available"
    return {
        "status": "healthy" if all_healthy else "degraded",
        "gateway": "MarineDataGateway",
        "service": "ORCA SIH26176",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": status,
    }

