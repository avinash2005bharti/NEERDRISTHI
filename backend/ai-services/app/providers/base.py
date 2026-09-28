"""
Base Provider Abstraction Layer for ORCA (SIH26176).
Every external or local data provider inherits from BaseProvider and implements
the standardized interface with strict normalization to Pydantic contracts.
"""
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
import httpx

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.core.security import redact_secrets, validate_external_url
    from app.core.resilience import CircuitBreaker, RateLimiter, retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ..core.security import redact_secrets, validate_external_url
    from ..core.resilience import CircuitBreaker, RateLimiter, retry_with_backoff
    from ..observability.logger import logger


class BaseProvider(ABC):
    """
    Abstract Base Provider.
    Mandates:
      - health_check()
      - fetch_current()
      - fetch_forecast()
      - normalize_response()
      - get_attribution()
      - get_data_timestamp()
      - get_confidence()
      - get_error_status()
    """

    def __init__(
        self,
        name: str,
        category: str,
        base_url: str = "",
        api_key: str = "",
        timeout_seconds: int = 30,
        rate_limit_per_second: float = 10.0,
        requires_api_key: bool = False,
    ):
        self.name = name
        self.category = category  # weather, marine, tide, geocoding, satellite, alerts
        self.base_url = (base_url or "").strip()
        self.api_key = (api_key or "").strip()
        self.timeout_seconds = timeout_seconds
        self.requires_api_key = requires_api_key

        self.circuit_breaker = CircuitBreaker(
            name=self.name,
            failure_threshold=4,
            recovery_time_seconds=30.0,
        )
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit_per_second)

    def is_configured(self) -> bool:
        """Returns True if provider has valid endpoint configured and key (if required)."""
        if not self.base_url:
            return False
        if self.requires_api_key and not self.api_key:
            return False
        return True

    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """Validate latitude between -90 and 90, longitude between -180 and 180."""
        try:
            lat = float(latitude)
            lon = float(longitude)
            return (-90.0 <= lat <= 90.0) and (-180.0 <= lon <= 180.0)
        except (ValueError, TypeError):
            return False

    def get_http_client(
        self,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.AsyncClient:
        headers = {
            "User-Agent": "ORCA-SIH26176/1.0 contact@example.com",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-api-key"] = self.api_key
        if custom_headers:
            headers.update(custom_headers)

        client_base_url = self.base_url if (self.base_url and validate_external_url(self.base_url, allow_http=True)) else ""
        client_timeout = float(timeout) if timeout is not None else float(self.timeout_seconds)

        class _AwaitableAsyncClient(httpx.AsyncClient):
            def __await__(self):
                async def _self():
                    return self
                return _self().__await__()

        return _AwaitableAsyncClient(
            base_url=client_base_url,
            headers=headers,
            timeout=client_timeout,
            follow_redirects=True,
        )

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if provider endpoint is configured, reachable, and operational."""
        pass

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        """Fetch current observation or latest data for given coordinates."""
        return None

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        """Fetch multi-hour or multi-day forecast for given coordinates."""
        return None

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        """Transform raw provider JSON/dataset into normalized Pydantic model."""
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        """Return legal source attribution, URL, license, and official status."""
        return {
            "source": self.name,
            "url": self.base_url,
            "category": self.category,
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        """Extract ISO 8601 timestamp representing issue or observation time."""
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        """Calculate confidence score between 0.0 and 1.0 based on data source quality."""
        return 0.90

    def get_error_status(self, exception_or_response: Any) -> Dict[str, Any]:
        """Generate structured error status without leaking secrets."""
        err_msg = redact_secrets(str(exception_or_response))
        return {
            "status": "DATA_UNAVAILABLE",
            "category": self.category,
            "provider": self.name,
            "reason": err_msg,
            "is_configured": self.is_configured(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
