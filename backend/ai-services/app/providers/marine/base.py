"""
Base Marine Provider Interface for ORCA.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..base import BaseProvider
from ...schemas.marine import MarineData


class BaseMarineProvider(BaseProvider, ABC):
    """Abstract interface for all marine sea-state providers."""

    @abstractmethod
    async def get_marine(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[MarineData]:
        """Fetch normalized marine sea-state data (wave height, period, direction, currents, SST)."""
        pass

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_marine(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_marine(latitude, longitude)

