from typing import TypedDict, Optional, List, Dict, Any, Tuple


class AgentState(TypedDict, total=False):
    request_id: str
    conversation_id: str
    query: str
    intent: str
    location: Optional[Dict[str, Any]]
    resolved_coordinates: Optional[Tuple[float, float]]  # (longitude, latitude)
    time_window: Optional[Dict[str, Any]]
    user_profile: Dict[str, Any]
    route: Optional[Dict[str, Any]]

    execution_plan: List[str]
    clarification_question: Optional[str]

    marine_data: Optional[Dict[str, Any]]
    weather_data: Optional[Dict[str, Any]]
    tide_data: Optional[Dict[str, Any]]
    geospatial_data: Optional[Dict[str, Any]]
    semantic_context: List[Dict[str, Any]]

    evidence: List[Dict[str, Any]]
    data_availability: Dict[str, str]

    safety_assessment: Optional[Dict[str, Any]]
    synthesis_output: Optional[Dict[str, Any]]
    agent_traces: List[Dict[str, Any]]

    status: str
    error: Optional[str]
