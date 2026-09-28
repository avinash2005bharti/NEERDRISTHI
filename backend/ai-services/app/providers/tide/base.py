"""
Base Tide Provider Interface for ORCA.
Provides tidal water-level heights and predictions.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..base import BaseProvider
from ...schemas.marine import TideData


class BaseTideProvider(BaseProvider, ABC):
    """Abstract interface for all tide and water-level providers."""

    @abstractmethod
    async def get_tide(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[TideData]:
        """Fetch normalized water-level observation or prediction."""
        pass
