"""
Provider Registry & Fallback Orchestrator for ORCA.
Coordinates primary and fallback providers with caching, timeouts, exponential backoff,
circuit breaking, and strict data availability semantics.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import time

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.core.config import settings
    from app.core.security import redact_secrets
    from app.observability.logger import logger
except (ImportError, ValueError):
    from .base import BaseProvider
    from ..core.config import settings
    from ..core.security import redact_secrets
    from ..observability.logger import logger


class ProviderRegistry:
    """
    Central registry for all external data providers.
    Supports dynamic fallback, health aggregation, and cache-backed query routing.
    """

    def __init__(self):
        self._providers: Dict[str, Dict[str, BaseProvider]] = {
            "weather": {},
            "marine": {},
            "geocoding": {},
            "tide": {},
            "satellite": {},
            "alerts": {},
        }
        self._in_memory_cache: Dict[str, Dict[str, Any]] = {}

    def register(self, category: str, provider_id: str, provider: BaseProvider):
        """Register a provider instance under a category."""
        if category not in self._providers:
            self._providers[category] = {}
        self._providers[category][provider_id] = provider
        logger.info(f"Registered provider [{category}]: {provider_id} ({provider.name})")

    def get_provider(self, category: str, provider_id: str) -> Optional[BaseProvider]:
        return self._providers.get(category, {}).get(provider_id)

    def list_providers(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered providers and their configuration status."""
        result = {}
        for cat, providers in self._providers.items():
            result[cat] = []
            for pid, prov in providers.items():
                attr = prov.get_attribution()
                result[cat].append({
                    "id": pid,
                    "name": prov.name,
                    "is_configured": prov.is_configured(),
                    "requires_api_key": prov.requires_api_key,
                    "base_url": prov.base_url,
                    "circuit_state": prov.circuit_breaker.state.value,
                    "attribution": attr,
                })
        return result

    async def check_all_health(self) -> Dict[str, Any]:
        """Perform health checks across all registered providers."""
        summary = {}
        for cat, providers in self._providers.items():
            summary[cat] = {}
            for pid, prov in providers.items():
                try:
                    summary[cat][pid] = await prov.health_check()
                except Exception as e:
                    summary[cat][pid] = {
                        "provider": prov.name,
                        "status": "error",
                        "error": redact_secrets(str(e)),
                    }
        return summary

    # ── Cache Helpers ────────────────────────────────────────────────────────

    def _get_cached(self, cache_key: str, max_age_seconds: int = 900) -> Optional[Dict[str, Any]]:
        cached = self._in_memory_cache.get(cache_key)
        if not cached:
            return None
        age = time.time() - cached["cached_at"]
        if age > max_age_seconds:
            # Stale
            return None
        return cached["data"]

    def _set_cached(self, cache_key: str, data: Any):
        self._in_memory_cache[cache_key] = {
            "cached_at": time.time(),
            "data": data,
        }

    # ── Orchestrated Fetching with Fallbacks ──────────────────────────────────

    async def fetch_weather_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        cache_key = f"weather:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = self._get_cached(cache_key, settings.CACHE_TTL_SECONDS)
        if cached:
            return cached

        # Preferred provider order
        primary_id = settings.WEATHER_PROVIDER or "open_meteo"
        candidate_ids = [primary_id] + [pid for pid in self._providers.get("weather", {}) if pid != primary_id]

        last_error = None
        for pid in candidate_ids:
            prov = self.get_provider("weather", pid)
            if not prov:
                continue
            if not prov.is_configured():
                continue
            try:
                data = await prov.fetch_forecast(latitude, longitude, **kwargs)
                if data and getattr(data, "data_status", "") != "DATA_UNAVAILABLE":
                    self._set_cached(cache_key, data)
                    return data
            except Exception as e:
                last_error = e
                logger.warning(f"Weather provider {pid} failed: {redact_secrets(str(e))}")

        # All failed or unconfigured
        return {
            "status": "DATA_UNAVAILABLE",
            "category": "weather",
            "reason": f"No available weather provider succeeded. Last error: {redact_secrets(str(last_error)) if last_error else 'Unconfigured'}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def fetch_marine_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        cache_key = f"marine:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = self._get_cached(cache_key, settings.CACHE_TTL_SECONDS)
        if cached:
            return cached

        primary_id = settings.MARINE_PROVIDER or "open_meteo"
        candidate_ids = [primary_id] + [pid for pid in self._providers.get("marine", {}) if pid != primary_id]

        last_error = None
        for pid in candidate_ids:
            prov = self.get_provider("marine", pid)
            if not prov:
                continue
            if not prov.is_configured():
                continue
            try:
                data = await prov.fetch_forecast(latitude, longitude, **kwargs)
                if data and getattr(data, "data_status", "") != "DATA_UNAVAILABLE":
                    self._set_cached(cache_key, data)
                    return data
            except Exception as e:
                last_error = e
                logger.warning(f"Marine provider {pid} failed: {redact_secrets(str(e))}")

        return {
            "status": "DATA_UNAVAILABLE",
            "category": "marine",
            "reason": f"No available marine wave provider succeeded. Last error: {redact_secrets(str(last_error)) if last_error else 'Unconfigured'}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def fetch_tide(self, latitude: float, longitude: float, **kwargs) -> Any:
        cache_key = f"tide:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = self._get_cached(cache_key, settings.CACHE_TTL_SECONDS)
        if cached:
            return cached

        # Strict order per requirements:
        # 1. Official tide provider (if configured)
        # 2. NOAA CO-OPS
        # 3. FES / TPXO
        # 4. Local tide-station dataset
        # 5. Fallback nearby water-level information
        provider_order = ["official", "noaa_coops", "fes_tpxo", "local_dataset", "water_level_fallback"]
        
        # If user explicitly configured TIDE_PROVIDER, try it first
        if settings.TIDE_PROVIDER and settings.TIDE_PROVIDER != "none" and settings.TIDE_PROVIDER in provider_order:
            provider_order.remove(settings.TIDE_PROVIDER)
            provider_order.insert(0, settings.TIDE_PROVIDER)

        for pid in provider_order:
            prov = self.get_provider("tide", pid)
            if not prov or not prov.is_configured():
                continue
            try:
                obs = await prov.fetch_current(latitude, longitude, **kwargs)
                if obs and getattr(obs, "data_status", "") != "DATA_UNAVAILABLE":
                    self._set_cached(cache_key, obs)
                    return obs
            except Exception as e:
                logger.warning(f"Tide provider {pid} failed: {redact_secrets(str(e))}")

        return {
            "status": "DATA_UNAVAILABLE",
            "category": "tide",
            "reason": "No configured tide provider for this location",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def fetch_satellite(self, latitude: float, longitude: float, **kwargs) -> Any:
        cache_key = f"sat:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = self._get_cached(cache_key, settings.CACHE_TTL_SECONDS)
        if cached:
            return cached

        primary_id = settings.SATELLITE_PROVIDER or "demo"
        candidate_ids = [primary_id] + [pid for pid in self._providers.get("satellite", {}) if pid != primary_id]

        for pid in candidate_ids:
            prov = self.get_provider("satellite", pid)
            if not prov or not prov.is_configured():
                continue
            try:
                obs = await prov.fetch_current(latitude, longitude, **kwargs)
                if obs and (not isinstance(obs, dict) or obs.get("status") != "DATA_UNAVAILABLE"):
                    self._set_cached(cache_key, obs)
                    return obs
            except Exception as e:
                logger.warning(f"Satellite provider {pid} failed: {redact_secrets(str(e))}")

        return {
            "status": "DATA_UNAVAILABLE",
            "category": "satellite",
            "reason": "No configured satellite ocean-color / SST provider for this location",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def fetch_alerts(self, latitude: Optional[float] = None, longitude: Optional[float] = None, **kwargs) -> List[Any]:
        primary_id = settings.ALERT_PROVIDER or "gdacs"
        candidate_ids = [primary_id] + [pid for pid in self._providers.get("alerts", {}) if pid != primary_id]

        for pid in candidate_ids:
            prov = self.get_provider("alerts", pid)
            if not prov or not prov.is_configured():
                continue
            try:
                alerts = await prov.fetch_current(latitude or 0.0, longitude or 0.0, **kwargs)
                if isinstance(alerts, list):
                    return alerts
            except Exception as e:
                logger.warning(f"Alerts provider {pid} failed: {redact_secrets(str(e))}")

        return []


provider_registry = ProviderRegistry()
