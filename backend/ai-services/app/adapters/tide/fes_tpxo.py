"""
FES / TPXO Global Tide Model Provider.
FES (Finite Element Solution) and TPXO (TOPEX/Poseidon global tidal model) provide global hydrodynamic tidal solutions.
Requires: Local NetCDF grid files or specialized OPeNDAP server.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.providers.base import BaseProvider
except (ImportError, ValueError):
    from ...providers.base import BaseProvider


class FESTPXOTideProvider(BaseProvider):
    def __init__(self, base_url: str = ""):
        super().__init__(
            name="FES-TPXO-Global-Tides",
            category="tide",
            base_url=base_url,
            requires_api_key=False,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "status": "unconfigured_optional_provider",
            "message": "FES/TPXO requires specialized hydrodynamic tidal grid files or OPeNDAP server.",
            "requires_configuration": True,
        }

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("FES/TPXO hydrodynamic tide service not configured in environment.")

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return self.get_error_status("FES/TPXO hydrodynamic tide service not configured in environment.")

    def normalize_response(self, raw_data: Any, **kwargs) -> Any:
        return None

    def get_attribution(self) -> Dict[str, str]:
        return {
            "source": "FES / TPXO Global Tidal Solution",
            "url": "https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html",
            "license": "Scientific / Open Data Research License",
            "notice": "FES tide solution produced by NOVELTIS, LEGOS and CLS Space Oceanography Division.",
            "type": "self_hostable_dataset",
            "requires_key": "false",
        }

    def get_data_timestamp(self, response: Any) -> Optional[str]:
        return None

    def get_confidence(self, response: Any) -> float:
        return 0.88


fes_tpxo_tide_provider = FESTPXOTideProvider()
