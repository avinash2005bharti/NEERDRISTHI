"""
Base Ocean Provider Interface for ORCA.
Provides Sea Surface Temperature (SST), Chlorophyll-a, salinity, and ocean biogeochemical data.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..base import BaseProvider
from ...schemas.marine import OceanBiology, MarineData


class BaseOceanProvider(BaseProvider, ABC):
    """Abstract interface for all ocean state and ocean color providers."""

    @abstractmethod
    async def get_ocean_state(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch combined ocean parameters: SST, chlorophyll, salinity, and physics."""
        pass

    @abstractmethod
    async def get_chlorophyll(
        self, latitude: float, longitude: float
    ) -> Optional[float]:
        """Fetch chlorophyll-a concentration in mg/m³."""
        pass

    @abstractmethod
    async def get_sst(
        self, latitude: float, longitude: float
    ) -> Optional[float]:
        """Fetch Sea Surface Temperature (SST) in Celsius."""
        pass
