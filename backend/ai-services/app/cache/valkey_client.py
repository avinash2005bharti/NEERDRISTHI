"""
Valkey/Redis cache client for ORCA Agent Core.
Provides a safe async cache interface that silently degrades when Valkey is unavailable.
Never caches unvalidated external API responses.
"""
from typing import Optional, Any, Dict
import json
from datetime import datetime, timezone
from ..config import settings
from ..observability.logger import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ValkeyCacheClient:
    """
    Async Valkey/Redis cache wrapper.

    TTL hierarchy (from config):
      weather:  VALKEY_TTL_WEATHER_SECONDS  (default 30 min)
      ocean:    VALKEY_TTL_OCEAN_SECONDS    (default 1 hr)
      pfz:      VALKEY_TTL_PFZ_SECONDS      (default 6 hr)
      alerts:   VALKEY_TTL_ALERTS_SECONDS   (default 15 min)
      geocode:  VALKEY_TTL_GEOCODE_SECONDS  (default 24 hr)
    """

    def __init__(self):
        self._client: Optional[Any] = None
        self._available: Optional[bool] = None  # None = untested yet

    async def _get_client(self) -> Optional[Any]:
        """
        Lazily connect to Valkey. Returns None if unavailable or unconfigured.
        """
        if not REDIS_AVAILABLE:
            return None
        if not settings.is_valkey_configured:
            return None
        if self._client is not None:
            return self._client
        try:
            client = aioredis.from_url(
                settings.VALKEY_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connectivity
            if client is not None:
                await client.ping()
                self._client = client
                self._available = True
                logger.info("Valkey cache connected successfully.")
        except Exception as e:
            logger.warning(f"Valkey cache unavailable: {e}. Continuing without cache.")
            self._client = None
            self._available = False
        return self._client

    def is_configured(self) -> bool:
        return REDIS_AVAILABLE and settings.is_valkey_configured

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a validated JSON payload from cache. Returns None on miss or error."""
        client = await self._get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            logger.info(f"Cache HIT: {key}")
            return data
        except Exception as e:
            logger.warning(f"Cache GET error for key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Store a validated JSON payload in cache with TTL. Returns True on success."""
        client = await self._get_client()
        if client is None:
            return False
        try:
            payload = {
                "__cached_at": datetime.now(timezone.utc).isoformat(),
                "__ttl_seconds": ttl_seconds,
                "data": value,
            }
            await client.setex(key, ttl_seconds, json.dumps(payload))
            logger.info(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache SET error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> None:
        """Remove a specific cache key."""
        client = await self._get_client()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception as e:
            logger.warning(f"Cache DELETE error for key '{key}': {e}")

    async def ping(self) -> bool:
        """Health check for cache connectivity."""
        client = await self._get_client()
        if client is None:
            return False
        try:
            return await client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Valkey connection gracefully."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


# Key builders — consistent naming for cache invalidation
class CacheKeys:
    @staticmethod
    def weather(lat: float, lon: float) -> str:
        # Round to 2 decimal places for reasonable locality grouping
        return f"weather:{lat:.2f}:{lon:.2f}"

    @staticmethod
    def marine_pfz(lat: float, lon: float) -> str:
        return f"pfz:{lat:.2f}:{lon:.2f}"

    @staticmethod
    def tide(lat: float, lon: float) -> str:
        return f"tide:{lat:.2f}:{lon:.2f}"

    @staticmethod
    def geocode(place_name: str) -> str:
        normalized = place_name.strip().lower().replace(" ", "_")
        return f"geocode:{normalized}"

    @staticmethod
    def marine_alerts(region: str) -> str:
        return f"alerts:{region.strip().lower()}"


cache_client = ValkeyCacheClient()
cache_keys = CacheKeys()
