"""
ORCA LangGraph Multi-Agent Workflow Engine.

Pipeline:
  START
  → planner (intent classification + plan)
  → conditional routing by intent:
      "safety_check" | "find_pfz"  → Full pipeline (weather + marine + geospatial)
      "route_safety"               → Full pipeline + route intersection
      "marine_status"              → Weather + Marine only (skip GIS if no route)
      "authority_monitoring"       → Geospatial + Marine
      clarification_required       → Early exit
  → [weather_sea_state, marine_pfz, semantic_memory] parallel (per plan)
  → geospatial (intersection checks)
  → safety_risk_engine (deterministic)
  → synthesis_agent
  → persist_audit_and_trace
  → END
"""
from typing import Dict, Any, List
import asyncio
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..agents.planner import planner_agent
from ..agents.geospatial import geospatial_agent
from ..agents.marine_pfz import marine_pfz_agent
from ..agents.weather_sea_state import weather_sea_state_agent
from ..agents.semantic_memory import semantic_memory_agent
from ..agents.synthesis import synthesis_agent
from ..safety.engine import safety_engine
from ..repositories.audit_repository import audit_repository
from ..observability.logger import logger

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# Intent-based execution plans
INTENT_PLANS: Dict[str, List[str]] = {
    "safety_check": ["weather", "marine", "memory", "geo"],
    "find_pfz": ["marine", "weather", "memory"],
    "route_safety": ["weather", "marine", "geo", "memory"],
    "marine_status": ["weather", "marine"],
    "authority_monitoring": ["geo", "marine", "weather"],
}

DEFAULT_PLAN = ["weather", "marine", "memory", "geo"]


class OrcaWorkflowEngine:
    """
    Multi-Agent LangGraph workflow execution engine for ORCA.

    Routing is intent-driven: the planner's identified intent determines
    which agents are activated and in what configuration.
    """

    async def run(self, initial_state: AgentState) -> AgentState:
        state = dict(initial_state)
        request_id = state.get("request_id", "unknown")
        logger.info(f"Starting workflow for requestId: {request_id}")

        # 1. Planner — classify intent, identify location needs
        planner_result = await planner_agent.execute(state)
        state.update(planner_result)

        # Early exit on clarification required
        if state.get("clarification_question"):
            state["status"] = "clarification_required"
            await self._persist_trace(state)
            return state

        # 2. Resolve intent and execution plan
        intent = state.get("intent", "safety_check")
        plan = INTENT_PLANS.get(intent, DEFAULT_PLAN)

        logger.info(f"Executing plan for intent='{intent}': {plan}")

        # 3. Location resolution (always first if coordinates needed)
        geo_initial = await geospatial_agent.execute(state)
        state.update(geo_initial)

        # 4. Conditionally run parallel data gathering
        tasks = []
        task_names = []

        if "weather" in plan:
            tasks.append(weather_sea_state_agent.execute(state))
            task_names.append("weather")

        if "marine" in plan:
            tasks.append(marine_pfz_agent.execute(state))
            task_names.append("marine")

        if "memory" in plan:
            tasks.append(semantic_memory_agent.execute(state))
            task_names.append("memory")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, res in zip(task_names, results):
                if isinstance(res, dict):
                    if "data_availability" in res:
                        state.setdefault("data_availability", {}).update(res["data_availability"])
                    if "evidence" in res:
                        existing_evidence = state.setdefault("evidence", [])
                        for ev in res["evidence"]:
                            if ev not in existing_evidence:
                                existing_evidence.append(ev)
                    for k, v in res.items():
                        if k not in ["data_availability", "evidence"]:
                            state[k] = v
                else:
                    logger.error(f"{name} agent exception: {res}")
                    if name == "weather":
                        state.setdefault("data_availability", {}).update({"weather": "unavailable", "tide": "unavailable"})
                    elif name == "marine":
                        state.setdefault("data_availability", {})["marine"] = "unavailable"
                    elif name == "memory":
                        state.setdefault("data_availability", {})["semanticMemory"] = "unavailable"

        # 5. Geospatial intersection check (post data fetch, only if in plan)
        if "geo" in plan:
            geo_post = await geospatial_agent.execute(state)
            if isinstance(geo_post, dict):
                if "data_availability" in geo_post:
                    state.setdefault("data_availability", {}).update(geo_post["data_availability"])
                for k, v in geo_post.items():
                    if k != "data_availability":
                        state[k] = v

        # 6. Deterministic Safety & Risk Evaluation (pure algorithmic, no LLM)
        user_profile = state.get("user_profile") or {}
        vessel_class = user_profile.get("vesselClass")
        risk_eval = safety_engine.evaluate(
            vessel_class=vessel_class,
            weather_data=state.get("weather_data"),
            marine_data=state.get("marine_data"),
            geospatial_data=state.get("geospatial_data"),
            data_availability=state.get("data_availability") or {},
            evidence_list=state.get("evidence") or [],
        )
        state["safety_assessment"] = risk_eval.model_dump()
        state.setdefault("agent_traces", []).append({
            "agent": "safety_risk_engine",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Deterministic verdict: {risk_eval.recommendation} ({risk_eval.risk_level}) | plan={plan}",
        })

        # 7. LLM synthesis — grounded in evidence only
        synthesis_result = await synthesis_agent.execute(state)
        state.update(synthesis_result)

        # 8. Determine response completeness
        data_avail = state.get("data_availability") or {}
        missing_count = sum(1 for s in data_avail.values() if s == "unavailable")
        state["status"] = "partial" if missing_count > 0 else "completed"

        # 9. Persist audit trail
        await self._persist_trace(state)

        logger.info(
            f"Workflow complete for requestId={request_id}. "
            f"Status={state['status']}, Recommendation={risk_eval.recommendation}, "
            f"Intent={intent}, Plan={plan}"
        )
        return state

    async def _persist_trace(self, state: AgentState) -> None:
        request_id = state.get("request_id", "unknown")
        traces = state.get("agent_traces", [])
        await audit_repository.save_trace(
            request_id=request_id,
            trace_data={
                "requestId": request_id,
                "agentStatuses": traces,
                "completedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        if state.get("safety_assessment"):
            await audit_repository.save_risk_assessment(
                request_id=request_id,
                assessment_data=state["safety_assessment"],
            )


workflow_engine = OrcaWorkflowEngine()
