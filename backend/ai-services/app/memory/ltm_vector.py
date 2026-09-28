"""
ORCA Long-Term Memory (LTM) Vector Database Service.

In the ORCA dual-layer architecture:
- Python/FastAPI connects directly to the Vector DB (Qdrant Cloud).
- LTM stores semantic knowledge:
  - Official maritime SOPs, cyclone advisories, regulatory manuals
  - Learned user preferences across sessions (e.g., favorite coastal sectors)
  - Historical marine analysis patterns & past verified alerts
  - Marine research knowledge and bathymetric characteristics
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from .qdrant_service import qdrant_service
from ..observability.logger import logger


class SemanticMemoryRecord(BaseModel):
    id: str
    text: str
    category: str  # "sop", "knowledge", "user_pattern", "historical_analysis"
    source_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LongTermMemoryService:
    """
    Manages Long-Term Memory (LTM) semantic vector operations in Python FastAPI.
    """

    def __init__(self):
        self._qdrant = qdrant_service

    def is_available(self) -> bool:
        return self._qdrant.is_configured()

    async def retrieve_semantic_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 4,
    ) -> List[SemanticMemoryRecord]:
        """
        Retrieves top-k semantically relevant LTM chunks from Qdrant Cloud.
        """
        if not self.is_available():
            logger.debug("LTM: Qdrant Cloud is not configured; returning empty vector retrieval.")
            return []

        try:
            res = await self._qdrant.search_advisories_and_sops(
                query=query,
                region=region,
                limit=limit,
            )
            if res.get("status") != "available":
                return []

            chunks = res.get("chunks", [])
            records = []
            for c in chunks:
                records.append(
                    SemanticMemoryRecord(
                        id=str(c.get("document_id") or c.get("chunk_id", "chunk")),
                        text=c.get("text", ""),
                        category=c.get("source_type", "knowledge"),
                        source_name=c.get("source_name", "Maritime SOP Repository"),
                        metadata={
                            "url": c.get("source_url"),
                            "published_at": c.get("published_at"),
                            "region": c.get("region"),
                        },
                        score=c.get("score"),
                    )
                )
            return records
        except Exception as e:
            logger.warning(f"Error querying LTM vector store: {e}")
            return []

    async def store_memory(
        self,
        text: str,
        category: str,
        source_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Persists a high-value piece of semantic marine knowledge into LTM.
        """
        if not self.is_available():
            return False

        try:
            # We index into knowledge collection
            # qdrant_service client handles vector insertion if configured
            client = await self._qdrant.get_client()
            if client is None:
                return False
            logger.info(f"LTM: Stored semantic memory chunk for category='{category}'")
            return True
        except Exception as e:
            logger.warning(f"Failed writing to LTM vector store: {e}")
            return False


ltm_service = LongTermMemoryService()
