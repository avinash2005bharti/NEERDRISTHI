from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from ..observability.logger import logger


class BaseDataAdapter(ABC):
    """
    Abstract base class for all real external data adapters.
    Adheres to the strict invariant: never fabricate data when unconfigured or failing.
    """

    def __init__(self, name: str, base_url: str, api_key: str = "", timeout_seconds: int = 15):
        self.name = name
        self.base_url = (base_url or "").strip()
        self.api_key = (api_key or "").strip()
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def get_client(self) -> httpx.AsyncClient:
        headers = {
            "User-Agent": "ORCA-Marine-Intelligence/1.0.0 (SIH26176)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-api-key"] = self.api_key

        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=float(self.timeout_seconds),
            follow_redirects=True,
        )

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if provider endpoint is configured and reachable."""
        pass
