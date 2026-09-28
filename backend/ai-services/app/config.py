from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(_ENV_PATH)),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Shared secret for internal gateway communication
    INTERNAL_SERVICE_SECRET: str = Field(default="", description="Secret shared between Gateway and Agent Core")
    JWT_SECRET: str = Field(default="", description="JWT Secret for token validation")

    # MongoDB
    MONGODB_URI: str = Field(default="", description="MongoDB connection string")
    MONGODB_DB_NAME: str = "orca"

    # Groq LLM
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq model name")
    GROQ_TEMPERATURE: float = 0.0
    GROQ_MAX_TOKENS: Optional[int] = 2048
    GROQ_TIMEOUT_SECONDS: int = 30

    # Qdrant Cloud
    QDRANT_URL: str = Field(default="", description="Qdrant cluster URL")
    QDRANT_API_KEY: str = Field(default="", description="Qdrant Cloud API key")
    QDRANT_COLLECTION_MEMORY: str = "orca_memory"
    QDRANT_COLLECTION_KNOWLEDGE: str = "orca_knowledge"

    # Swappable Embeddings
    EMBEDDING_PROVIDER: str = Field(default="", description="Provider for vector embeddings")
    EMBEDDING_API_KEY: str = Field(default="", description="API key for embedding provider")
    EMBEDDING_MODEL: str = Field(default="", description="Embedding model identifier")

    # Weather Provider — defaults to Open-Meteo (open-data, free, no API key required)
    WEATHER_PROVIDER: str = Field(default="open_meteo", description="Weather provider: open_meteo, noaa, ecmwf")
    WEATHER_BASE_URL: str = Field(default="https://api.open-meteo.com", description="Atmospheric weather service base URL")
    WEATHER_API_KEY: str = Field(default="", description="Weather service API key (blank for Open-Meteo)")
    WEATHER_FORECAST_ENDPOINT: str = Field(default="/v1/forecast", description="Atmospheric forecast API path")

    # Marine Waves & Sea State Provider — defaults to Open-Meteo Marine
    MARINE_PROVIDER: str = Field(default="open_meteo", description="Marine provider: open_meteo, copernicus, noaa")
    MARINE_BASE_URL: str = Field(default="https://marine-api.open-meteo.com", description="Open-Meteo Marine base URL")
    MARINE_API_KEY: str = Field(default="", description="Marine service API key")
    MARINE_FORECAST_ENDPOINT: str = Field(default="/v1/marine", description="Marine wave forecast API path")

    # Backward compatibility aliases
    OPEN_METEO_MARINE_URL: str = Field(default="https://marine-api.open-meteo.com", description="Legacy alias for MARINE_BASE_URL")
    WAVE_FORECAST_ENDPOINT: str = Field(default="/v1/marine", description="Legacy alias for MARINE_FORECAST_ENDPOINT")

    # Geocoding — Nominatim / OpenStreetMap
    GEOCODER_PROVIDER: str = Field(default="nominatim", description="Geocoder provider: nominatim, photon")
    GEOCODER_BASE_URL: str = Field(default="https://nominatim.openstreetmap.org", description="Coastal geocoding base URL")
    GEOCODER_API_KEY: str = Field(default="", description="Geocoder API key (not required for Nominatim)")
    GEOCODER_USER_AGENT: str = Field(default="ORCA-SIH26176/1.0 contact@example.com", description="User-Agent for Nominatim OSM policy")
    GEOCODER_ENDPOINT: str = Field(default="/search", description="Geocoder search path")
    GEOCODER_RATE_LIMIT_PER_SECOND: float = Field(default=1.0, description="Max requests per second for geocoder")

    # Tide Provider
    TIDE_PROVIDER: str = Field(default="local_dataset", description="Tide provider: official, noaa_coops, fes_tpxo, local_dataset, none")
    TIDE_BASE_URL: str = Field(default="", description="Tide service base URL")
    TIDE_API_KEY: str = Field(default="", description="Tide service API key")
    TIDE_ENDPOINT: str = Field(default="", description="Tide service API path")
    TIDE_STATION_ID: str = Field(default="", description="Configured tide station ID")

    # Satellite & Ocean-Color Provider (SST, Chlorophyll-a)
    SATELLITE_PROVIDER: str = Field(default="demo", description="Satellite provider: demo, copernicus, nasa, erddap, none")
    SATELLITE_BASE_URL: str = Field(default="", description="Satellite data base URL")
    SATELLITE_API_KEY: str = Field(default="", description="Satellite service API key")
    SATELLITE_DATASET: str = Field(default="", description="Dataset identifier")

    # Cyclone & Severe Weather Alerts Provider
    ALERT_PROVIDER: str = Field(default="gdacs", description="Alert provider: gdacs, imd, noaa_nhc, computed, none")
    ALERT_BASE_URL: str = Field(default="", description="Alert service base URL")
    ALERT_API_KEY: str = Field(default="", description="Alert service API key")

    # Legacy INCOIS (kept for optional official access)
    INCOIS_BASE_URL: str = Field(default="", description="INCOIS marine data base URL")
    INCOIS_API_KEY: str = Field(default="", description="INCOIS portal API token")
    INCOIS_PFZ_ENDPOINT: str = Field(default="", description="INCOIS PFZ advisory path")
    INCOIS_OCEAN_STATE_ENDPOINT: str = Field(default="", description="INCOIS Ocean State Forecast path")

    # Valkey / Redis caching
    VALKEY_URL: str = Field(default="", description="Valkey or Redis connection URL")
    VALKEY_TTL_WEATHER_SECONDS: int = Field(default=1800, description="Weather cache TTL: 30 minutes")
    VALKEY_TTL_OCEAN_SECONDS: int = Field(default=3600, description="Ocean/wave cache TTL: 1 hour")
    VALKEY_TTL_ALERTS_SECONDS: int = Field(default=900, description="Alerts cache TTL: 15 minutes")
    VALKEY_TTL_GEOCODE_SECONDS: int = Field(default=86400, description="Geocode cache TTL: 24 hours")
    VALKEY_TTL_PFZ_SECONDS: int = Field(default=21600, description="PFZ cache TTL: 6 hours")

    # MET Norway Weather Fallback
    MET_NO_ENABLED: bool = Field(default=True, description="Enable MET Norway weather fallback")
    MET_NO_BASE_URL: str = Field(default="https://api.met.no", description="MET Norway base URL")
    MET_NO_ENDPOINT: str = Field(default="/weatherapi/locationforecast/2.0/complete", description="MET Norway endpoint")
    MET_NO_USER_AGENT: str = Field(default="ORCA-SIH26176-Hackathon/1.0 (contact: student-team@sih26176.in)", description="User-Agent for MET Norway")

    # INCOIS ERDDAP Public Ocean Data
    INCOIS_ERDDAP_ENABLED: bool = Field(default=True, description="Enable INCOIS ERDDAP public ocean data")
    INCOIS_ERDDAP_BASE_URL: str = Field(default="https://erddap.incois.gov.in/erddap", description="INCOIS ERDDAP base URL")
    INCOIS_OFFICIAL_ENABLED: bool = Field(default=False, description="Enable official INCOIS credentials if available")

    # Copernicus Marine Service
    COPERNICUS_ENABLED: bool = Field(default=False, description="Enable Copernicus Marine service")
    COPERNICUS_USERNAME: str = Field(default="", description="Copernicus Marine username")
    COPERNICUS_PASSWORD: str = Field(default="", description="Copernicus Marine password")

    # WorldTides
    WORLDTIDES_ENABLED: bool = Field(default=False, description="Enable WorldTides API")
    WORLDTIDES_API_KEY: str = Field(default="", description="WorldTides API key")

    # Provider Runtime & Fallback
    ENABLE_PROVIDER_FALLBACK: bool = Field(default=True, description="Enable automatic provider fallback")
    PROVIDER_TIMEOUT_SECONDS: int = Field(default=15, description="Timeout per provider request")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=15, description="Request timeout in seconds")
    EXTERNAL_RETRY_ATTEMPTS: int = Field(default=2, description="Maximum retry attempts with backoff")
    MAX_DATA_FRESHNESS_MINUTES: int = Field(default=360, description="Maximum age of data before marked stale")
    CACHE_TTL_SECONDS: int = Field(default=900, description="Default in-memory cache TTL")
    DEMO_MODE: bool = Field(default=True, description="Enable local demo mode for satellite/tide data")

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def is_qdrant_configured(self) -> bool:
        return bool(self.QDRANT_URL and self.QDRANT_URL.strip() and self.QDRANT_API_KEY and self.QDRANT_API_KEY.strip())

    @property
    def is_mongo_configured(self) -> bool:
        return bool(self.MONGODB_URI and self.MONGODB_URI.strip())

    @property
    def is_incois_configured(self) -> bool:
        return bool(self.INCOIS_BASE_URL and self.INCOIS_BASE_URL.strip())

    @property
    def is_weather_configured(self) -> bool:
        return bool(self.WEATHER_BASE_URL and self.WEATHER_BASE_URL.strip())

    @property
    def is_tide_configured(self) -> bool:
        return bool(self.TIDE_BASE_URL and self.TIDE_BASE_URL.strip()) or self.TIDE_PROVIDER in ["noaa_coops", "local_dataset"]

    @property
    def is_geocoder_configured(self) -> bool:
        return bool(self.GEOCODER_BASE_URL and self.GEOCODER_BASE_URL.strip())

    @property
    def is_valkey_configured(self) -> bool:
        return bool(self.VALKEY_URL and self.VALKEY_URL.strip())


settings = Settings()
