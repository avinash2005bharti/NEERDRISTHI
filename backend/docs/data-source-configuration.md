# ORCA Real Data Source Configuration & Payload Mapping Guide

> **Important Invariant:** ORCA is built with a zero-fabrication constraint. It connects to external data sources **only** when official endpoints and credentials are provided via environment variables. In the absence of credentials, ORCA emits structured `DATA_UNAVAILABLE` states and safely defaults to `INSUFFICIENT_DATA` or `NO_GO`.

---

## 1. Environment Variable Reference

Configure these in `apps/agent-core/.env`:

```bash
# Official INCOIS Endpoints
INCOIS_BASE_URL=https://incois.gov.in/portal
INCOIS_API_KEY=
INCOIS_PFZ_ENDPOINT=/api/pfz/v1/advisories
INCOIS_OCEAN_STATE_ENDPOINT=/api/osf/v1/forecast

# Official Meteorological Endpoints
WEATHER_BASE_URL=https://api.metagency.gov.in
WEATHER_API_KEY=
WEATHER_FORECAST_ENDPOINT=/v1/marine/forecast
WAVE_FORECAST_ENDPOINT=/v1/marine/wave

# Official Tide Observation Endpoints
TIDE_BASE_URL=https://tide.incois.gov.in
TIDE_API_KEY=
TIDE_ENDPOINT=/api/tides/station

# Coastal Geocoder
GEOCODER_BASE_URL=https://nominatim.openstreetmap.org
GEOCODER_API_KEY=
GEOCODER_ENDPOINT=/search

# Groq LLM Reasoning
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0
GROQ_MAX_TOKENS=2048
GROQ_TIMEOUT_SECONDS=30

# Qdrant Cloud Semantic Memory
QDRANT_URL=https://xxxx-your-cluster.qdrant.io:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_MEMORY=orca_memory
QDRANT_COLLECTION_KNOWLEDGE=orca_knowledge

# Swappable Vector Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 2. Real Data Adapter Mapping Instructions

Each adapter is housed in `apps/agent-core/app/integrations/` and contains marked `TODO` sections where official data schemas should be parsed.

### 2.1 INCOIS Marine & PFZ Adapter (`incois_adapter.py`)
1. **Target File:** `apps/agent-core/app/integrations/incois_adapter.py`
2. **Method:** `fetch_pfz(latitude, longitude)`
3. **Official INCOIS Bulletin Format:**
   INCOIS typically issues multi-spectral Potential Fishing Zone advisories based on NOAA-AVHRR sea surface temperature (SST) and Oceansat-2/MODIS chlorophyll imagery.
4. **Mapping Guidance:**
   ```python
   # Locate the TODO in incois_adapter.py:
   for feat in raw_data.get("features", []):
       props = feat.get("properties", {})
       geom = feat.get("geometry", {})
       # Map INCOIS attributes:
       sst = props.get("SeaSurfaceTemperature") or props.get("sst")
       chlorophyll = props.get("ChlorophyllConcentration") or props.get("chlorophyll")
       depth = props.get("WaterDepth") or props.get("depth")
       valid_to = props.get("ExpiryDate") or props.get("valid_to")
   ```

---

### 2.2 Weather and Wave Adapter (`weather_adapter.py`)
1. **Target File:** `apps/agent-core/app/integrations/weather_adapter.py`
2. **Method:** `fetch_weather_and_waves(latitude, longitude)`
3. **Mandatory Standard Units:**
   - **Wind Speed:** Must be in **meters per second (m/s)**. If the provider returns knots, convert using: `speed_mps = knots * 0.514444`. If in km/h, convert using: `speed_mps = kmh * 0.277778`.
   - **Wave Height:** Must be in **meters (m)** (significant wave height $H_s$).
   - **Precipitation:** Must be in **millimeters (mm)**.
4. **Mapping Guidance:**
   ```python
   # Locate the TODO in weather_adapter.py:
   # Example Open-Meteo marine schema mapping:
   current = raw.get("current", {})
   wind_speed = current.get("wind_speed_10m", 0.0) # in m/s
   wave_height = current.get("wave_height", 0.0)   # in meters
   precip = current.get("precipitation", 0.0)       # in mm
   ```

---

### 2.3 Tide Observation Adapter (`tide_adapter.py`)
1. **Target File:** `apps/agent-core/app/integrations/tide_adapter.py`
2. **Method:** `fetch_tide(latitude, longitude, station_name)`
3. **Mandatory Standard Units:**
   - **Tide Height:** Must be in **meters (m)** above Chart Datum.
   - **Timestamp:** ISO 8601 string (`YYYY-MM-DDTHH:MM:SSZ`).
4. **Mapping Guidance:**
   ```python
   # Locate the TODO in tide_adapter.py:
   tide_height = raw.get("tide_level_m") or raw.get("water_level", 0.0)
   observed_at = raw.get("reading_timestamp_utc")
   ```

---

### 2.4 Coastal Geocoder Adapter (`geocoder_adapter.py`)
1. **Target File:** `apps/agent-core/app/integrations/geocoder_adapter.py`
2. **Method:** `resolve_place_name(place_name)`
3. **Output:** Normalized `(longitude, latitude)` coordinate tuple.
4. **Mapping Guidance:**
   Standard OpenStreetMap Nominatim or custom coastal landing center directory:
   ```python
   lat = float(item["lat"])
   lon = float(item["lon"])
   ```

---

## 3. Groq LLM API Configuration

1. Obtain an API key from [Groq Console](https://console.groq.com).
2. Set in `apps/agent-core/.env`:
   ```bash
   GROQ_API_KEY=gsk_yourRealGroqApiKeyHere
   GROQ_MODEL=llama-3.3-70b-versatile
   GROQ_TEMPERATURE=0
   ```
3. **Safety Guarantee:** The Groq client is only invoked by the `synthesis_agent` after the deterministic safety engine has rendered its verdict. The LLM cannot modify the verdict, cannot invent unobserved conditions, and cannot hallucinate fishing zones.

---

## 4. Qdrant Cloud Semantic Memory Configuration

1. Create a free cluster on [Qdrant Cloud](https://cloud.qdrant.io).
2. Copy the Cluster URL and API key into `apps/agent-core/.env`:
   ```bash
   QDRANT_URL=https://your-cluster-id.us-east4-0.gcp.cloud.qdrant.io:6333
   QDRANT_API_KEY=your-qdrant-api-key
   ```
3. At application startup, `app/memory/qdrant_service.py` will automatically initialize collections:
   - `orca_memory`: User preferences and past session summaries.
   - `orca_knowledge`: Official maritime SOPs, cyclone safety manuals, and regulatory boundaries.
4. If Qdrant credentials are not configured, semantic search returns `disabled`, and the rest of the marine safety workflow operates without interruption.
