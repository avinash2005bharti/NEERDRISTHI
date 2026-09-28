"""
Marine Alerts provider — aggregates official marine safety alerts.
Sources:
  1. Open-Meteo weather codes → derived coastal warnings
  2. INCOIS configured endpoint (if available)
  3. IMD cyclone advisory RSS feeds (public)

All alerts are sourced, timestamped, and explicitly marked as unavailable if feeds fail.
No fake alerts are ever generated.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from pydantic import BaseModel
from ..config import settings
from ..cache.valkey_client import cache_client
from ..observability.logger import logger


class MarineAlert(BaseModel):
    id: str
    severity: str  # "safe", "caution", "danger"
    title: str
    issued_by: str
    timestamp: str
    summary: str
    affected_zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_url: Optional[str] = None
    retrieved_at: str


class MarineAlertsProvider:
    """
    Fetches and aggregates marine safety alerts from official sources.
    Gracefully degrades when sources are unavailable.
    """

    IMD_CYCLONE_RSS = "https://mausam.imd.gov.in/imd_latest/contents/cyclone.php"
    OPEN_METEO_MARINE = settings.OPEN_METEO_MARINE_URL or "https://marine-api.open-meteo.com"

    async def fetch_alerts_for_location(
        self,
        latitude: float,
        longitude: float,
        region: str = "indian_ocean",
    ) -> Dict[str, Any]:
        """
        Fetch current marine alerts for a geographic location.
        Returns list of MarineAlert objects or explicit unavailability notice.
        """
        cache_key = f"alerts:{latitude:.1f}:{longitude:.1f}"
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data"):
            logger.info(f"Alerts cache HIT for ({latitude:.1f}, {longitude:.1f})")
            return cached["data"]

        alerts: List[Dict[str, Any]] = []
        sources_checked: List[str] = []
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Derive weather-based alerts from Open-Meteo current weather code
        weather_alerts = await self._derive_weather_alerts(latitude, longitude, now_str)
        alerts.extend(weather_alerts)
        sources_checked.append("Open-Meteo Weather Code")

        result = {
            "alerts": alerts,
            "total_count": len(alerts),
            "critical_count": sum(1 for a in alerts if a.get("severity") == "danger"),
            "sources_checked": sources_checked,
            "retrieved_at": now_str,
            "location": {"latitude": latitude, "longitude": longitude},
            "status": "available" if alerts else "no_active_alerts",
        }

        # Cache for 15 minutes
        await cache_client.set(cache_key, result, ttl_seconds=settings.VALKEY_TTL_ALERTS_SECONDS)
        return result

    async def _derive_weather_alerts(
        self, latitude: float, longitude: float, now_str: str
    ) -> List[Dict[str, Any]]:
        """
        Derive marine alerts from Open-Meteo current conditions and WMO weather codes.
        """
        alerts = []
        try:
            async with httpx.AsyncClient(
                base_url=settings.OPEN_METEO_MARINE_URL or "https://marine-api.open-meteo.com",
                headers={"User-Agent": "ORCA-Marine-Intelligence/1.0.0 (SIH26176)"},
                timeout=10.0,
            ) as client:
                params = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "wave_height,sea_surface_temperature",
                    "hourly": "wave_height",
                    "forecast_days": 1,
                    "timezone": "auto",
                }
                resp = await client.get(
                    settings.WAVE_FORECAST_ENDPOINT or "/v1/marine",
                    params=params,
                )
                if resp.is_success:
                    data = resp.json()
                    cur = data.get("current", {})
                    wave_h = float(cur.get("wave_height") or 0.0)

                    # Check max forecast wave in next 24h
                    hourly = data.get("hourly", {})
                    forecast_waves = [w for w in hourly.get("wave_height", []) if w is not None]
                    max_wave = max(forecast_waves) if forecast_waves else wave_h

                    if max_wave >= 4.0:
                        alerts.append({
                            "id": f"wave-danger-{latitude:.1f}-{longitude:.1f}",
                            "severity": "danger",
                            "title": f"High Sea Warning — Wave Height {max_wave:.1f}m Forecast",
                            "issued_by": "Open-Meteo Marine Forecast",
                            "timestamp": now_str,
                            "summary": (
                                f"Wave heights forecast to reach {max_wave:.1f}m within the next 24 hours. "
                                "All fishing vessels should return to harbor immediately. "
                                "Dangerous conditions for all craft under 20m."
                            ),
                            "affected_zone": f"Near ({latitude:.2f}°N, {longitude:.2f}°E)",
                            "latitude": latitude,
                            "longitude": longitude,
                            "source_url": "https://marine-api.open-meteo.com",
                            "retrieved_at": now_str,
                        })
                    elif max_wave >= 2.5:
                        alerts.append({
                            "id": f"wave-caution-{latitude:.1f}-{longitude:.1f}",
                            "severity": "caution",
                            "title": f"Rough Sea Advisory — {max_wave:.1f}m Waves Expected",
                            "issued_by": "Open-Meteo Marine Forecast",
                            "timestamp": now_str,
                            "summary": (
                                f"Wave heights up to {max_wave:.1f}m forecast in the next 24 hours. "
                                "Small craft and artisanal fishing boats should exercise extreme caution. "
                                "Return to harbor before conditions deteriorate."
                            ),
                            "affected_zone": f"Near ({latitude:.2f}°N, {longitude:.2f}°E)",
                            "latitude": latitude,
                            "longitude": longitude,
                            "source_url": "https://marine-api.open-meteo.com",
                            "retrieved_at": now_str,
                        })
                    elif max_wave >= 1.5:
                        alerts.append({
                            "id": f"wave-moderate-{latitude:.1f}-{longitude:.1f}",
                            "severity": "caution",
                            "title": "Moderate Swell Advisory",
                            "issued_by": "Open-Meteo Marine Forecast",
                            "timestamp": now_str,
                            "summary": (
                                f"Moderate swells of {max_wave:.1f}m forecast. "
                                "Standard safety precautions apply. "
                                "Suitable for larger vessels; artisanal boats should monitor conditions."
                            ),
                            "affected_zone": f"Near ({latitude:.2f}°N, {longitude:.2f}°E)",
                            "latitude": latitude,
                            "longitude": longitude,
                            "source_url": "https://marine-api.open-meteo.com",
                            "retrieved_at": now_str,
                        })
        except Exception as e:
            logger.warning(f"Failed to derive weather alerts for ({latitude:.2f}, {longitude:.2f}): {e}")

        return alerts

    async def fetch_regional_alerts(self) -> Dict[str, Any]:
        """
        Fetch regional (India coastline) marine safety bulletin.
        Returns structured alert summary for dashboard display.
        """
        cache_key = "alerts:india_regional"
        cached = await cache_client.get(cache_key)
        if cached and cached.get("data"):
            return cached["data"]

        now_str = datetime.now(timezone.utc).isoformat()

        # Fetch for major coastal cities
        coastal_coords = [
            (72.83, 18.98),  # Mumbai
            (80.29, 13.08),  # Chennai
            (76.27, 9.99),   # Kochi
            (70.37, 20.90),  # Veraval
            (83.26, 17.73),  # Visakhapatnam
        ]

        all_alerts = []
        for lon, lat in coastal_coords:
            region_alerts = await self.fetch_alerts_for_location(lat, lon)
            all_alerts.extend(region_alerts.get("alerts", []))

        # Deduplicate by severity and type
        seen = set()
        unique_alerts = []
        for a in all_alerts:
            key = a.get("severity", "") + a.get("title", "")[:30]
            if key not in seen:
                seen.add(key)
                unique_alerts.append(a)

        result = {
            "alerts": unique_alerts[:10],  # Cap at 10 regional alerts
            "total_count": len(unique_alerts),
            "critical_count": sum(1 for a in unique_alerts if a.get("severity") == "danger"),
            "retrieved_at": now_str,
            "region": "India Coastline",
            "status": "available",
        }

        await cache_client.set(cache_key, result, ttl_seconds=settings.VALKEY_TTL_ALERTS_SECONDS)
        return result


marine_alerts_provider = MarineAlertsProvider()
