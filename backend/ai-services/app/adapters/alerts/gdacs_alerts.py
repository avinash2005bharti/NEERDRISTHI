"""
GDACS (Global Disaster Alert and Coordination System) Adapter.
Open, public disaster alert feed maintained jointly by the United Nations (OCHA)
and the European Commission (DG ECHO / JRC).
Public feed URL: https://www.gdacs.org/xml/rss.xml
"""
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import httpx

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
    from app.schemas.normalized import MarineAlert
    from app.core.config import settings
    from app.core.resilience import retry_with_backoff
    from app.observability.logger import logger
except (ImportError, ValueError):
    from ...providers.base import BaseProvider
    from ...schemas.normalized import MarineAlert
    from ...core.config import settings
    from ...core.resilience import retry_with_backoff
    from ...observability.logger import logger


class GDACSAlertProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="GDACS-Disaster-Alerts",
            category="alerts",
            base_url="https://www.gdacs.org",
            requires_api_key=False,
        )
        self.rss_path = "/xml/rss.xml"

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self.get_http_client()
            async with client:
                res = await client.get(self.rss_path, timeout=5.0)
                return {
                    "provider": self.name,
                    "status": "healthy" if res.is_success else "degraded",
                    "http_status": res.status_code,
                }
        except Exception as e:
            return {"provider": self.name, "status": "unreachable", "error": str(e)}

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> List[MarineAlert]:
        """Fetch tropical cyclone and severe storm alerts from GDACS."""
        alerts: List[MarineAlert] = []

        async def _call():
            client = await self.get_http_client()
            async with client:
                res = await client.get(self.rss_path, timeout=8.0)
                res.raise_for_status()
                return res.text

        try:
            xml_text = await retry_with_backoff(
                _call,
                max_attempts=settings.EXTERNAL_RETRY_ATTEMPTS,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.name,
            )
            alerts = self.parse_gdacs_rss(xml_text, latitude, longitude)
        except Exception as e:
            logger.warning(f"GDACS RSS fetch failed: {e}")

        return alerts

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.fetch_current(latitude, longitude, **kwargs)

    def parse_gdacs_rss(self, xml_text: str, req_lat: float, req_lon: float) -> List[MarineAlert]:
        alerts = []
        try:
            root = ET.fromstring(xml_text)
            channel = root.find("channel")
            if channel is None:
                return []

            now_str = datetime.now(timezone.utc).isoformat()
            items = channel.findall("item")

            for item in items:
                title = item.findtext("title", "")
                link = item.findtext("link", "https://www.gdacs.org")
                pub_date = item.findtext("pubDate", now_str)
                desc = item.findtext("description", "")

                # Filter for Cyclones and Tropical Storms
                if any(k in title.lower() for k in ["cyclone", "tropical storm", "depression", "hurricane", "typhoon"]):
                    severity = "Severe" if "red" in desc.lower() else ("Moderate" if "orange" in desc.lower() else "Minor")
                    alerts.append(
                        MarineAlert(
                            alert_id=f"GDACS-{abs(hash(title)) % 1000000}",
                            issuing_agency="GDACS / UN OCHA / European Commission",
                            event_type="Tropical Cyclone / Marine Storm Advisory",
                            severity=severity,
                            urgency="Immediate",
                            certainty="Observed",
                            affected_area=title,
                            issue_time=pub_date,
                            expiry_time=None,
                            instruction="Check national meteorological warning bulletin immediately. Suspend open-sea navigation.",
                            official_url=link,
                        )
                    )
        except Exception as e:
            logger.warning(f"Error parsing GDACS RSS XML: {e}")
        return alerts

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return raw_data

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "Global Disaster Alert and Coordination System (GDACS)",
            "url": "https://www.gdacs.org",
            "license": "Public Open Data / United Nations OCHA",
            "notice": "Disaster alert feeds provided by GDACS (UN OCHA / EC JRC).",
            "type": "open_data",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()

    def get_confidence(self, response: Any) -> float:
        return 0.90


gdacs_alert_provider = GDACSAlertProvider()
