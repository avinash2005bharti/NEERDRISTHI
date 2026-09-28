from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from ..config import settings
from ..observability.logger import logger


class BaseEmbeddingAdapter(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> Optional[List[List[float]]]:
        pass


class SwappableEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    Swappable embedding client interface supporting Google Gemini, OpenAI, and custom vector providers.
    Groq is strictly for LLM reasoning and does not generate embeddings.
    """

    def __init__(self):
        self.provider = (settings.EMBEDDING_PROVIDER or "").lower().strip()
        self.api_key = (settings.EMBEDDING_API_KEY or "").strip()
        self.model = (settings.EMBEDDING_MODEL or "").strip()

        # Sensible model defaults per provider
        if not self.model:
            if self.provider in ("gemini", "google"):
                self.model = "gemini-embedding-2"
            else:
                self.model = "text-embedding-3-small"

    def is_configured(self) -> bool:
        return bool(self.provider and self.api_key)

    async def embed_query(self, text: str) -> Optional[List[float]]:
        if not self.is_configured():
            logger.debug("Embedding provider unconfigured. Skipping vector embedding generation.")
            return None

        # ─── Google Gemini / Generative Language API ──────────────────────────
        if self.provider in ("gemini", "google"):
            model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:embedContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        url,
                        json={
                            "model": model_name,
                            "content": {"parts": [{"text": text}]},
                        },
                    )
                    if res.status_code == 200:
                        data = res.json()
                        values = data.get("embedding", {}).get("values")
                        if values:
                            return values
                    else:
                        logger.error(f"Gemini embedding error: HTTP {res.status_code} - {res.text[:200]}")
            except Exception as e:
                logger.error(f"Error in Gemini embedding query: {e}")
            return None

        # ─── OpenAI Compatible Provider ───────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"input": text, "model": self.model},
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.error(f"OpenAI embedding error: HTTP {res.status_code} - {res.text[:200]}")
        except Exception as e:
            logger.error(f"Error in OpenAI embedding query: {e}")
        return None

    async def embed_documents(self, texts: List[str]) -> Optional[List[List[float]]]:
        if not self.is_configured() or not texts:
            return None

        # ─── Google Gemini Batch Embeddings ───────────────────────────────────
        if self.provider in ("gemini", "google"):
            model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:batchEmbedContents?key={self.api_key}"
            try:
                requests_payload = [
                    {
                        "model": model_name,
                        "content": {"parts": [{"text": t}]},
                    }
                    for t in texts
                ]
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, json={"requests": requests_payload})
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = [item.get("values", []) for item in data.get("embeddings", [])]
                        return embeddings
                    else:
                        logger.error(f"Gemini batch embedding error: HTTP {res.status_code} - {res.text[:200]}")
            except Exception as e:
                logger.error(f"Error in Gemini batch embedding: {e}")
            return None

        # ─── OpenAI Batch Embeddings ──────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"input": texts, "model": self.model},
                )
                if res.status_code == 200:
                    data = res.json()
                    return [d["embedding"] for d in data["data"]]
                else:
                    logger.error(f"OpenAI batch embedding error: HTTP {res.status_code} - {res.text[:200]}")
        except Exception as e:
            logger.error(f"Error in OpenAI batch embedding: {e}")
        return None


embedding_adapter = SwappableEmbeddingAdapter()
