"""
Base Weather Provider Interface for ORCA.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..base import BaseProvider
from ...schemas.marine import WeatherData, DataSource


class BaseWeatherProvider(BaseProvider, ABC):
    """Abstract interface for all atmospheric weather providers."""

    @abstractmethod
    async def get_weather(
        self, latitude: float, longitude: float, date: Optional[str] = None
    ) -> Optional[WeatherData]:
        """Fetch normalized atmospheric weather data."""
        pass

    async def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_weather(latitude, longitude)

    async def fetch_forecast(self, latitude: float, longitude: float, **kwargs) -> Any:
        return await self.get_weather(latitude, longitude)

