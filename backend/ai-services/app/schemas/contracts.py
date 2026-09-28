from typing import List, Optional, Literal, Union, Dict, Any
from pydantic import BaseModel, Field
from .geojson import LineStringGeometry


UserRole = Literal["fisherman", "authority", "disaster_manager", "admin"]
QueryIntent = Literal["safety_check", "find_pfz", "route_safety", "marine_status", "authority_monitoring"]
ResponseStatus = Literal["completed", "partial", "clarification_required", "failed"]
SafetyRecommendation = Literal["GO", "GO_WITH_CAUTION", "NO_GO", "INSUFFICIENT_DATA"]
RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"]
DataAvailabilityStatus = Literal["available", "unavailable", "stale", "not_requested"]
EvidenceCategory = Literal["marine", "weather", "tide", "geospatial", "memory", "safety"]
EvidenceFreshness = Literal["fresh", "stale", "unknown"]


class LocationInput(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TimeWindowInput(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    label: Optional[str] = None


class UserProfileInput(BaseModel):
    role: UserRole = "fisherman"
    vesselClass: Optional[str] = "motorized_fiberglass"
    language: Optional[str] = "en"


class OrcaQueryRequest(BaseModel):
    conversationId: Optional[str] = None
    query: str
    intent: Optional[QueryIntent] = None
    location: Optional[LocationInput] = None
    timeWindow: Optional[TimeWindowInput] = None
    userProfile: Optional[UserProfileInput] = None
    route: Optional[LineStringGeometry] = None


class DataAvailability(BaseModel):
    marine: DataAvailabilityStatus = "not_requested"
    weather: DataAvailabilityStatus = "not_requested"
    tide: DataAvailabilityStatus = "not_requested"
    geospatial: DataAvailabilityStatus = "not_requested"
    semanticMemory: Literal["available", "unavailable", "not_requested"] = "not_requested"


class EvidenceItem(BaseModel):
    category: EvidenceCategory
    name: str
    value: Union[str, int, float, bool, Dict[str, Any], List[Any]]
    unit: Optional[str] = None
    observedAt: Optional[str] = None
    validUntil: Optional[str] = None
    retrievedAt: str
    sourceName: str
    sourceUrl: Optional[str] = None
    freshness: EvidenceFreshness = "unknown"


class SafetyAssessment(BaseModel):
    triggeredRules: List[str] = Field(default_factory=list)
    missingData: List[str] = Field(default_factory=list)
    requiredNextAction: str


class AgentStatusTrace(BaseModel):
    agent: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    timestamp: str
    details: Optional[str] = None


class OrcaTrace(BaseModel):
    requestId: str
    agentStatuses: List[AgentStatusTrace] = Field(default_factory=list)
    startedAt: str
    completedAt: str


class OrcaQueryResponse(BaseModel):
    requestId: str
    conversationId: str
    status: ResponseStatus
    recommendation: Optional[SafetyRecommendation] = None
    riskLevel: RiskLevel
    riskScore: int = Field(ge=0, le=100)
    confidenceScore: int = Field(ge=0, le=100)
    answer: str
    language: str = "en"
    clarificationQuestion: Optional[str] = None
    dataAvailability: DataAvailability
    evidence: List[EvidenceItem] = Field(default_factory=list)
    safety: SafetyAssessment
    trace: OrcaTrace
