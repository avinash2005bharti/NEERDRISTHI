from .base import BaseWeatherProvider
from .open_meteo import OpenMeteoWeatherProvider, open_meteo_weather
from .met_no import MetNorwayWeatherProvider, met_norway_weather

met_no_weather = met_norway_weather

__all__ = [
    "BaseWeatherProvider",
    "OpenMeteoWeatherProvider",
    "open_meteo_weather",
    "MetNorwayWeatherProvider",
    "met_norway_weather",
    "met_no_weather",
]
