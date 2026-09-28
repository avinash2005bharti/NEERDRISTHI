"""
Base Fishing Zone Provider Interface for ORCA.
Provides Potential Fishing Zone (PFZ) advisories and candidate zones.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from ..base import BaseProvider
from ...schemas.marine import FishingZone


class BaseFishingZoneProvider(BaseProvider, ABC):
    """Abstract interface for all fishing zone providers."""

    @abstractmethod
    async def get_fishing_zones(
        self,
        latitude: float,
        longitude: float,
        sst: Optional[float] = None,
        chlorophyll: Optional[float] = None,
        current_velocity: Optional[float] = None,
    ) -> List[FishingZone]:
        """Fetch or derive candidate fishing zones."""
        pass
