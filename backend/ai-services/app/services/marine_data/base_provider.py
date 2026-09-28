"""
Base Marine Data Provider Interface for ORCA (SIH26176).
Standardizes methods for retrieving oceanographic, atmospheric, and navigational layers.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple


class MarineDataProvider(ABC):
    """
    Abstract interface for all oceanographic data sources.
    Implementations must return structured dictionaries or GeoJSON FeatureCollections.
    """

    def __init__(self, name: str, is_live_source: bool = True):
        self.name = name
        self.is_live_source = is_live_source

    @abstractmethod
    async def get_sst(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get Sea Surface Temperature (SST) layer or point data."""
        pass

    @abstractmethod
    async def get_chlorophyll(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get Chlorophyll-a ocean color layer or point data."""
        pass

    @abstractmethod
    async def get_waves(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get wave height, period, direction, and swell data."""
        pass

    @abstractmethod
    async def get_wind(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get wind speed, direction, and gusts."""
        pass

    @abstractmethod
    async def get_tides(
        self,
        lat: float,
        lon: float,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get tidal heights, harmonic predictions, and water level context."""
        pass

    @abstractmethod
    async def get_pfz(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get Potential Fishing Zone (PFZ) advisory polygons."""
        pass

    @abstractmethod
    async def get_risk(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get marine hazard zones, navigational risk buffers, and restricted areas."""
        pass

    @abstractmethod
    async def get_overview(
        self,
        lat: float,
        lon: float,
    ) -> Optional[Dict[str, Any]]:
        """Get consolidated marine overview at point."""
        pass
