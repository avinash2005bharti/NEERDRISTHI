from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal, cast
from ..schemas.contracts import (
    OrcaQueryRequest,
    OrcaQueryResponse,
    DataAvailability,
    DataAvailabilityStatus,
    ResponseStatus,
    RiskLevel,
    SafetyRecommendation,
    EvidenceItem,
    SafetyAssessment,
    AgentStatusTrace,
    OrcaTrace,
)
from ..schemas.agent_state import AgentState
from ..graph.workflow import workflow_engine
from ..repositories.audit_repository import audit_repository
from ..observability.logger import logger


def _normalize_data_status(val: Any) -> DataAvailabilityStatus:
    if val in ("available", "unavailable", "stale", "not_requested"):
        return cast(DataAvailabilityStatus, val)
    return "not_requested"


def _normalize_memory_status(
    val: Any,
) -> Literal["available", "unavailable", "not_requested"]:
    if val in ("available", "unavailable", "not_requested"):
        return cast(Literal["available", "unavailable", "not_requested"], val)
    return "not_requested"


def _normalize_response_status(val: Any) -> ResponseStatus:
    if val in ("completed", "partial", "clarification_required", "failed"):
        return cast(ResponseStatus, val)
    return "completed"


def _normalize_agent_status(
    val: Any,
) -> Literal["pending", "running", "completed", "failed", "skipped"]:
    if val in ("pending", "running", "completed", "failed", "skipped"):
        return cast(
            Literal["pending", "running", "completed", "failed", "skipped"], val
        )
    return "completed"


def _normalize_risk_level(val: Any) -> RiskLevel:
    if isinstance(val, str) and val in ("LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"):
        return cast(RiskLevel, val)
    return "UNKNOWN"


def _normalize_recommendation(val: Any) -> Optional[SafetyRecommendation]:
    if isinstance(val, str) and val in ("GO", "GO_WITH_CAUTION", "NO_GO", "INSUFFICIENT_DATA"):
        return cast(SafetyRecommendation, val)
    return None


def _normalize_score(val: Any, default: int = 0) -> int:
    try:
        score = (round(float(val)))
        return max(0, min(100, score))
    except (TypeError, ValueError):
        return default


class AgentCoreOrchestrator:
    """
    Service orchestrator mapping API request payloads to LangGraph agent state,
    and transforming workflow execution results into the canonical OrcaQueryResponse contract.
    """

    async def execute_query(
        self, request: OrcaQueryRequest, request_id: str
    ) -> OrcaQueryResponse:
        started_at = datetime.now(timezone.utc).isoformat()
        conversation_id = request.conversationId or request_id

        # Convert request to AgentState
        initial_state: AgentState = {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "query": request.query,
            "intent": request.intent or "safety_check",
            "location": request.location.model_dump() if request.location else None,
            "time_window": request.timeWindow.model_dump() if request.timeWindow else None,
            "user_profile": request.userProfile.model_dump() if request.userProfile else {},
            "route": request.route.model_dump() if request.route else None,
            "evidence": [],
            "data_availability": {
                "marine": "not_requested",
                "weather": "not_requested",
                "tide": "not_requested",
                "geospatial": "not_requested",
                "semanticMemory": "not_requested",
            },
            "agent_traces": [],
            "status": "pending",
        }

        # Run multi-agent workflow
        final_state = await workflow_engine.run(initial_state)
        completed_at = datetime.now(timezone.utc).isoformat()

        # Extract safety assessment
        safety_dict = final_state.get("safety_assessment") or {}
        safety_assessment = SafetyAssessment(
            triggeredRules=safety_dict.get("triggered_rules") or [],
            missingData=safety_dict.get("missing_data") or [],
            requiredNextAction=safety_dict.get(
                "required_next_action",
                "No physical safety hazards detected. Exercise standard maritime diligence.",
            ) or "No physical safety hazards detected. Exercise standard maritime diligence.",
        )

        # Normalize data availability
        raw_avail = final_state.get("data_availability") or {}
        data_availability = DataAvailability(
            marine=_normalize_data_status(raw_avail.get("marine")),
            weather=_normalize_data_status(raw_avail.get("weather")),
            tide=_normalize_data_status(raw_avail.get("tide")),
            geospatial=_normalize_data_status(raw_avail.get("geospatial")),
            semanticMemory=_normalize_memory_status(raw_avail.get("semanticMemory")),
        )

        # Extract evidence list
        evidence_items: List[EvidenceItem] = []
        for ev in final_state.get("evidence", []):
            try:
                if isinstance(ev, EvidenceItem):
                    evidence_items.append(ev)
                elif isinstance(ev, dict):
                    evidence_items.append(EvidenceItem(**ev))
            except Exception as e:
                logger.debug(f"Skipping non-conforming evidence item: {e}")

        # Assemble trace
        agent_statuses = [
            AgentStatusTrace(
                agent=str(tr.get("agent") or "unknown"),
                status=_normalize_agent_status(tr.get("status")),
                timestamp=str(tr.get("timestamp") or completed_at),
                details=tr.get("details"),
            )
            for tr in final_state.get("agent_traces", [])
            if isinstance(tr, dict)
        ]
        trace = OrcaTrace(
            requestId=request_id,
            agentStatuses=agent_statuses,
            startedAt=started_at,
            completedAt=completed_at,
        )

        synthesis_output = final_state.get("synthesis_output") or {}
        clarification_q = final_state.get("clarification_question")
        user_prof = final_state.get("user_profile") or {}
        detected_lang = user_prof.get("language") or "en"

        if clarification_q:
            answer = clarification_q
            language = detected_lang
        else:
            answer = synthesis_output.get("answer") or (
                "ORCA processing complete. Please inspect data availability and evidence items."
            )
            language = synthesis_output.get("language") or detected_lang

        response = OrcaQueryResponse(
            requestId=request_id,
            conversationId=conversation_id,
            status=_normalize_response_status(final_state.get("status")),
            recommendation=_normalize_recommendation(safety_dict.get("recommendation")),
            riskLevel=_normalize_risk_level(safety_dict.get("risk_level")),
            riskScore=_normalize_score(safety_dict.get("risk_score"), 0),
            confidenceScore=_normalize_score(safety_dict.get("confidence_score"), 0),
            answer=answer,
            language=language,
            clarificationQuestion=clarification_q,
            dataAvailability=data_availability,
            evidence=evidence_items,
            safety=safety_assessment,
            trace=trace,
        )

        # Save query to audit repository
        try:
            await audit_repository.save_query_result(request_id, response.model_dump())
        except Exception as e:
            logger.warning(f"Failed to persist query result in audit cache: {e}")

        return response


orchestrator = AgentCoreOrchestrator()

