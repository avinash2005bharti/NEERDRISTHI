"""
Base Geocoder Provider Interface for ORCA.
Provides forward geocoding (place name to coordinates) and reverse geocoding (coordinates to place name).
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from ..base import BaseProvider
from ...schemas.marine import Location


class BaseGeocoderProvider(BaseProvider, ABC):
    """Abstract interface for all geocoding providers."""

    @abstractmethod
    async def geocode(self, query: str) -> Optional[Location]:
        """Convert a place name, harbor, or coastal feature into a Location with coordinates."""
        pass

    @abstractmethod
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """Convert coordinates into a human-readable coastal or place name."""
        pass
