from typing import Dict, Any, List
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..memory.qdrant_service import qdrant_service
from ..observability.logger import logger


class SemanticMemoryAgent:
    """
    Semantic Memory Agent.
    Interacts with Qdrant Cloud to retrieve maritime SOPs, cyclone manuals,
    and historical advisory records.
    Strictly distinguishes historical reference documents from live observations.
    """

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        query = state.get("query", "")
        data_availability: Dict[str, str] = {}
        evidence = list(state.get("evidence") or [])
        semantic_context: List[Dict[str, Any]] = []

        res = await qdrant_service.search_advisories_and_sops(query=query)

        if res.get("status") == "available":
            data_availability["semanticMemory"] = "available"
            chunks = res.get("chunks", [])
            semantic_context = chunks

            for chunk in chunks:
                evidence.append({
                    "category": "memory",
                    "name": f"Maritime Guidance: {chunk.get('source_name')}",
                    "value": chunk.get("text", "")[:300],
                    "observedAt": chunk.get("published_at"),
                    "validUntil": None,
                    "retrievedAt": datetime.now(timezone.utc).isoformat(),
                    "sourceName": chunk.get("source_name", "Qdrant SOP Repository"),
                    "sourceUrl": chunk.get("source_url"),
                    "freshness": "fresh",
                })
        else:
            data_availability["semanticMemory"] = "unavailable"

        trace_entry = {
            "agent": "semantic_memory",
            "status": "completed" if data_availability.get("semanticMemory") == "available" else "skipped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Semantic memory status: {data_availability.get('semanticMemory')}",
        }
        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "semantic_context": semantic_context,
            "evidence": evidence,
            "data_availability": data_availability,
            "agent_traces": current_traces,
        }


semantic_memory_agent = SemanticMemoryAgent()
