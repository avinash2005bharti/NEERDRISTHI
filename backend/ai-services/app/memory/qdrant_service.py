from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from ..config import settings
from .embedding_adapter import embedding_adapter
from ..observability.logger import logger


class MemoryChunkPayload(BaseModel):
    document_id: str
    chunk_id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    source_url: Optional[str] = None
    source_name: str
    source_type: str  # e.g., "advisory", "sop", "regulation", "cyclone_protocol"
    published_at: Optional[str] = None
    retrieved_at: str
    validity_start: Optional[str] = None
    validity_end: Optional[str] = None
    region: Optional[str] = None
    language: str = "en"
    trust_level: str = "official"  # "official", "verified", "user_report"
    checksum: str
    text: str


class QdrantMemoryService:
    """
    Semantic memory interface to Qdrant Cloud.
    If Qdrant credentials are missing, returns typed disabled/unavailable status without failing queries.
    Never stores or retrieves fabricated knowledge.
    """

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self.memory_collection = settings.QDRANT_COLLECTION_MEMORY
        self.knowledge_collection = settings.QDRANT_COLLECTION_KNOWLEDGE

    def is_configured(self) -> bool:
        return settings.is_qdrant_configured

    async def get_client(self) -> Optional[AsyncQdrantClient]:
        if not self.is_configured():
            return None
        if self._client is None:
            try:
                self._client = AsyncQdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=10.0,
                )
                logger.info("Connected to Qdrant Cloud cluster.")
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant Cloud client: {e}")
                return None
        return self._client

    async def initialize_collections(self, vector_size: int = 1536) -> None:
        """
        Create required Qdrant collections only if credentials exist.
        """
        client = await self.get_client()
        if client is None:
            return

        for col in [self.memory_collection, self.knowledge_collection]:
            try:
                exists = await client.collection_exists(col)
                if not exists:
                    await client.create_collection(
                        collection_name=col,
                        vectors_config=qmodels.VectorParams(
                            size=vector_size,
                            distance=qmodels.Distance.COSINE,
                        ),
                    )
                    logger.info(f"Created Qdrant collection: {col}")
            except Exception as e:
                logger.warning(f"Failed ensuring Qdrant collection '{col}': {e}")

    async def search_advisories_and_sops(
        self,
        query: str,
        region: Optional[str] = None,
        language: str = "en",
        limit: int = 4,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant advisory history and operational SOPs from Qdrant Cloud.
        """
        if not self.is_configured():
            return {
                "status": "unavailable",
                "reason": "QDRANT_URL or QDRANT_API_KEY is not configured.",
                "chunks": [],
            }

        client = await self.get_client()
        if client is None or not embedding_adapter.is_configured():
            return {
                "status": "unavailable",
                "reason": "Vector embedding provider is unconfigured.",
                "chunks": [],
            }

        try:
            query_vector = await embedding_adapter.embed_query(query)
            if not query_vector:
                return {
                    "status": "unavailable",
                    "reason": "Failed to generate query vector embedding.",
                    "chunks": [],
                }

            # Build metadata filter
            conditions = []
            if region:
                conditions.append(
                    qmodels.FieldCondition(
                        key="region",
                        match=qmodels.MatchValue(value=region),
                    )
                )

            query_filter = qmodels.Filter(must=conditions) if conditions else None

            results = await client.search(
                collection_name=self.knowledge_collection,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )

            chunks = []
            for hit in results:
                payload = hit.payload or {}
                chunks.append({
                    "score": hit.score,
                    "text": payload.get("text", ""),
                    "source_name": payload.get("source_name", "Official SOP"),
                    "source_url": payload.get("source_url"),
                    "source_type": payload.get("source_type", "document"),
                    "published_at": payload.get("published_at"),
                    "trust_level": payload.get("trust_level", "official"),
                })

            return {
                "status": "available",
                "chunks": chunks,
            }

        except Exception as e:
            logger.error(f"Error searching Qdrant Cloud: {e}")
            return {
                "status": "unavailable",
                "reason": f"Qdrant query error: {str(e)}",
                "chunks": [],
            }


qdrant_service = QdrantMemoryService()
