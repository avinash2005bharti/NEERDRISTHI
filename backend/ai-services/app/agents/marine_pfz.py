from typing import Dict, Any, List
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..integrations.incois_adapter import incois_adapter
from ..utils.freshness import calculate_freshness
from ..repositories.mongo_client import get_db
from ..observability.logger import logger


class MarinePFZAgent:
    """
    Marine and PFZ Agent.
    Interacts strictly with official INCOIS marine endpoints.
    Never invents or fabricates fishing zones or SST values.
    """

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        coords = state.get("resolved_coordinates")
        evidence = list(state.get("evidence") or [])
        data_availability: Dict[str, str] = {}

        marine_data: Dict[str, Any] = {}

        if not coords:
            data_availability["marine"] = "unavailable"
            marine_data["status"] = "unavailable"
            marine_data["reason"] = "Location coordinates unavailable for marine query."
        else:
            lon, lat = coords
            result = await incois_adapter.fetch_pfz(latitude=lat, longitude=lon)

            if isinstance(result, list) and len(result) > 0:
                data_availability["marine"] = "available"
                marine_data["pfz_records"] = [r.model_dump() for r in result]
                marine_data["status"] = "available"

                # Persist to MongoDB pfz_zones collection
                db = get_db()
                if db:
                    for rec in result:
                        try:
                            await db["pfz_zones"].replace_one(
                                {"id": rec.id},
                                rec.model_dump(),
                                upsert=True,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to upsert PFZ to MongoDB: {e}")

                # Add evidence item
                for rec in result:
                    freshness = calculate_freshness(rec.valid_from)
                    evidence.append({
                        "category": "marine",
                        "name": f"PFZ Zone {rec.id}",
                        "value": {
                            "sst_celsius": rec.sst_celsius,
                            "chlorophyll_mg_m3": rec.chlorophyll_mg_m3,
                            "depth_meters": rec.depth_meters,
                            "distance_km": rec.distance_km,
                        },
                        "observedAt": rec.valid_from,
                        "validUntil": rec.valid_to,
                        "retrievedAt": rec.retrieved_at,
                        "sourceName": "INCOIS PFZ Bulletin",
                        "sourceUrl": rec.source_url,
                        "freshness": freshness,
                    })
            else:
                data_availability["marine"] = "unavailable"
                marine_data["status"] = "unavailable"
                reason = result.reason if hasattr(result, "reason") else "No PFZ data returned"
                marine_data["reason"] = reason

        trace_entry = {
            "agent": "marine_pfz",
            "status": "completed" if data_availability["marine"] == "available" else "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Marine data status: {data_availability.get('marine')}",
        }
        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "marine_data": marine_data,
            "evidence": evidence,
            "data_availability": data_availability,
            "agent_traces": current_traces,
        }


marine_pfz_agent = MarinePFZAgent()
