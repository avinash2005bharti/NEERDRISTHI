"""
ORCA In-Memory Audit Repository.
Maintains transient recent execution traces and query results in Python memory.
Full persistent storage for Short-Term Memory and user audit is owned exclusively by Node.js + MongoDB.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from ..observability.logger import logger


class AuditRepository:
    """
    In-memory audit cache for agent execution traces and query results.
    Primary database persistence is handled by Node.js.
    """

    def __init__(self, db_getter=None):
        self._traces: Dict[str, Dict[str, Any]] = {}
        self._queries: Dict[str, Dict[str, Any]] = {}
        self._assessments: Dict[str, Dict[str, Any]] = {}
        self._max_entries = 500

    async def save_trace(self, request_id: str, trace_data: Dict[str, Any]) -> None:
        if len(self._traces) > self._max_entries:
            # Evict oldest entry
            oldest = next(iter(self._traces))
            del self._traces[oldest]
        self._traces[request_id] = {
            "requestId": request_id,
            "trace": trace_data,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        }

    async def save_risk_assessment(self, request_id: str, assessment_data: Dict[str, Any]) -> None:
        if len(self._assessments) > self._max_entries:
            oldest = next(iter(self._assessments))
            del self._assessments[oldest]
        self._assessments[request_id] = {
            "requestId": request_id,
            "assessment": assessment_data,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        }

    async def save_query_result(self, request_id: str, payload: Dict[str, Any]) -> None:
        if len(self._queries) > self._max_entries:
            oldest = next(iter(self._queries))
            del self._queries[oldest]
        self._queries[request_id] = {
            "requestId": request_id,
            "data": payload,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

    async def get_query_result(self, request_id: str) -> Optional[Dict[str, Any]]:
        record = self._queries.get(request_id)
        return record.get("data") if record else None


audit_repository = AuditRepository()
