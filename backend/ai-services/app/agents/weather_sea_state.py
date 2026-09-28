from typing import Dict, Any, List
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..integrations.weather_adapter import weather_adapter
from ..integrations.tide_adapter import tide_adapter
from ..utils.freshness import calculate_freshness
from ..repositories.mongo_client import get_db
from ..observability.logger import logger


class WeatherSeaStateAgent:
    """
    Weather and Sea-State Agent.
    Interacts strictly with configured official weather, wave, and tide providers.
    Never invents or fabricates wave heights, wind speeds, or barometric alerts.
    """

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        coords = state.get("resolved_coordinates")
        evidence = list(state.get("evidence") or [])
        data_availability: Dict[str, str] = {}

        weather_data: Dict[str, Any] = {}
        tide_data: Dict[str, Any] = {}

        if not coords:
            data_availability["weather"] = "unavailable"
            data_availability["tide"] = "unavailable"
            weather_data["status"] = "unavailable"
            weather_data["reason"] = "Coordinates unavailable for weather lookup."
        else:
            lon, lat = coords

            # 1. Fetch weather and sea-state observations
            weather_res = await weather_adapter.fetch_weather_and_waves(latitude=lat, longitude=lon)

            if hasattr(weather_res, "wind_speed_mps"):
                freshness = calculate_freshness(weather_res.observed_at)
                data_availability["weather"] = freshness if freshness in ["available", "stale"] else "available"
                weather_data = weather_res.model_dump()
                weather_data["status"] = "available"
                weather_data["freshness"] = freshness

                # Persist snapshot to MongoDB
                db = get_db()
                if db:
                    try:
                        await db["weather_snapshots"].insert_one(weather_res.model_dump())
                    except Exception as e:
                        logger.warning(f"Failed to record weather snapshot to MongoDB: {e}")

                # Add evidence item
                evidence.append({
                    "category": "weather",
                    "name": "Significant Wave Height",
                    "value": weather_res.wave_height_meters,
                    "unit": "meters",
                    "observedAt": weather_res.observed_at,
                    "validUntil": weather_res.valid_until,
                    "retrievedAt": weather_res.retrieved_at,
                    "sourceName": weather_res.provider,
                    "sourceUrl": weather_res.source_url,
                    "freshness": freshness,
                })
                evidence.append({
                    "category": "weather",
                    "name": "Wind Speed",
                    "value": weather_res.wind_speed_mps,
                    "unit": "m/s",
                    "observedAt": weather_res.observed_at,
                    "validUntil": weather_res.valid_until,
                    "retrievedAt": weather_res.retrieved_at,
                    "sourceName": weather_res.provider,
                    "sourceUrl": weather_res.source_url,
                    "freshness": freshness,
                })
                if weather_res.warning_flag:
                    evidence.append({
                        "category": "safety",
                        "name": "Meteorological Warning Flag",
                        "value": weather_res.warning_flag,
                        "observedAt": weather_res.observed_at,
                        "validUntil": weather_res.valid_until,
                        "retrievedAt": weather_res.retrieved_at,
                        "sourceName": weather_res.provider,
                        "sourceUrl": weather_res.source_url,
                        "freshness": freshness,
                    })
            else:
                data_availability["weather"] = "unavailable"
                weather_data["status"] = "unavailable"
                weather_data["reason"] = (
                    weather_res.reason if hasattr(weather_res, "reason") else "No weather response"
                )

            # 2. Fetch tide observation
            tide_res = await tide_adapter.fetch_tide(latitude=lat, longitude=lon)
            if hasattr(tide_res, "tide_height_meters"):
                tide_freshness = calculate_freshness(tide_res.observed_at)
                data_availability["tide"] = "available"
                tide_data = tide_res.model_dump()
                tide_data["status"] = "available"

                evidence.append({
                    "category": "tide",
                    "name": "Tide Water Level",
                    "value": tide_res.tide_height_meters,
                    "unit": "meters",
                    "observedAt": tide_res.observed_at,
                    "validUntil": None,
                    "retrievedAt": tide_res.retrieved_at,
                    "sourceName": tide_res.provider,
                    "sourceUrl": tide_res.source_url,
                    "freshness": tide_freshness,
                })
            else:
                data_availability["tide"] = "unavailable"
                tide_data["status"] = "unavailable"
                tide_data["reason"] = (
                    tide_res.reason if hasattr(tide_res, "reason") else "No tide response"
                )

        trace_entry = {
            "agent": "weather_sea_state",
            "status": "completed" if data_availability.get("weather") == "available" else "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Weather: {data_availability.get('weather')}, Tide: {data_availability.get('tide')}",
        }
        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "weather_data": weather_data,
            "tide_data": tide_data,
            "evidence": evidence,
            "data_availability": data_availability,
            "agent_traces": current_traces,
        }


weather_sea_state_agent = WeatherSeaStateAgent()
