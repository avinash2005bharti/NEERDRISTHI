# ORCA Marine Data Architecture & Provider Gateway (SIH26176)

## 1. Executive Overview

ORCA (**Marine Ecosystem Reasoning with Collaborative AI Agents**) is designed for Smart India Hackathon problem **SIH26176**.

The core requirement of this architecture is to provide production-grade, highly resilient meteorological, oceanographic, and geospatial data services for marine safety and coastal fishing communities along India's 7,516 km coastline.

Previously, the architecture depended directly on restricted or unavailable institutional REST APIs. The upgraded architecture establishes a centralized **Marine Data Gateway** (`MarineDataGateway`) utilizing legally usable open-source, open-data, and free-tier scientific data providers, featuring multi-tier fallback, coordinate validation, intelligent caching, provenance tracking, and explicit regulatory compliance labeling.

```
                         ORCA
                          |
                     LangGraph
                       Planner
                          |
                   Marine Data Gateway
                          |
        +-----------------+------------------+
        |                 |                  |
   Open-Meteo       INCOIS ERDDAP      Copernicus
        |                 |                  |
   Weather/Waves      SST/CHL          Ocean State
   Currents/SST       Ocean Data       Currents/SST
        |                 |                  |
        +-----------------+------------------+
                          |
                    Data Normalizer
                          |
             +------------+-------------+
             |            |             |
          Weather       Marine        Fishing
           Agent        Agent          Agent
             |            |             |
             +------------+-------------+
                          |
                      Risk Agent
                          |
                   Synthesis Agent
                          |
                    ORCA Response
```

---

## 2. Critical Architectural Invariant: Gateway Isolation

**LangGraph agents must NEVER call external APIs directly.**
All HTTP requests (`requests.get`, `httpx.get`, `aiohttp`, etc.) are forbidden inside agent code.

Agents interact exclusively with the internal `marine_data_gateway`:
- `get_weather_forecast(latitude, longitude, date)`
- `get_marine_conditions(latitude, longitude, date)`
- `get_ocean_conditions(latitude, longitude, date)`
- `get_tide(latitude, longitude, date)`
- `get_chlorophyll(latitude, longitude)`
- `get_sst(latitude, longitude)`
- `get_fishing_zones(latitude, longitude)`
- `geocode_location(place_name)`
- `reverse_geocode(latitude, longitude)`

---

## 3. Provider Architecture & Tiered Priority

```
FastAPI /api/marine/* & Internal Adapters
   │
   ▼
Marine Data Gateway (`app.providers.gateway.marine_data_gateway`)
   ├── Weather Provider:
   │     ├── Primary: Open-Meteo Weather API (ECMWF/DWD models)
   │     └── Fallback: MET Norway (Locationforecast/2.0)
   ├── Marine Provider:
   │     ├── Primary: Open-Meteo Marine API (Waves, swell, currents, SST)
   │     ├── Secondary: INCOIS ERDDAP (SST, ocean parameters)
   │     └── Tertiary: Copernicus Marine Service (CMEMS - Optional)
   ├── Ocean Provider:
   │     ├── Primary: INCOIS ERDDAP (`IRS_chlorophyll_datasets`, `incois_argo_sst_weekly`)
   │     └── Advanced: Copernicus Marine Service (Biogeochemistry & L4 SST)
   ├── Tide & Sea-Level Provider:
   │     ├── Primary: Open-Meteo Marine (Modeled ocean surface elevation above MSL)
   │     └── Optional: WorldTides (Harmonic tide tables when configured)
   ├── Geocoder Provider:
   │     └── Nominatim / OpenStreetMap (Coastal-biased forward & reverse geocoding)
   └── Fishing Zone Provider:
         ├── Institutional: Official INCOIS PFZ (Enabled only with institutional API credentials)
         └── Algorithmic: ORCA AI-Derived Candidate Fishing Zones (Thermal fronts & chlorophyll)
```

---

## 4. Provider Specifications

### 4.1 Open-Meteo Weather (Atmospheric Primary)
- **Base URL**: `https://api.open-meteo.com`
- **Endpoint**: `/v1/forecast`
- **Variables**: `temperature_2m`, `apparent_temperature`, `precipitation`, `rain`, `weather_code`, `wind_speed_10m` (converted to m/s), `wind_direction_10m`, `wind_gusts_10m`, `surface_pressure`, `cloud_cover`, `visibility`.
- **Authentication**: None required (Free open data tier).
- **Rate Limit**: 10 requests/second, 10,000/day.

### 4.2 Open-Meteo Marine (Sea-State Primary)
- **Base URL**: `https://marine-api.open-meteo.com`
- **Endpoint**: `/v1/marine`
- **Variables**: `wave_height`, `wave_direction`, `wave_period`, `swell_wave_height`, `swell_wave_direction`, `sea_surface_temperature`, `ocean_current_velocity`, `ocean_current_direction`, `sea_level`.
- **Authentication**: None required.
- **Rate Limit**: 10 requests/second.

### 4.3 INCOIS ERDDAP (Ocean Biology & Physics)
- **Base URL**: `https://erddap.incois.gov.in/erddap`
- **Authentication**: Public open access. No API key required for machine-readable tabledap/griddap endpoints.
- **Verified Active Datasets**:
  - `IRS_chlorophyll_datasets`: IRS P4 OCM satellite Chlorophyll-a.
  - `incois_oceansat2_datasets`: Oceansat-2 ocean color.
  - `incois_argo_sst_weekly`: ARGO float weekly Sea Surface Temperature analysis.
  - `NOAA_AVHRR_AMSR_datasets`: High-resolution daily satellite SST analysis.
  - `ascat_daily_datasets`: ASCAT satellite daily ocean surface wind field.
- **Error Handling**: Graceful fallback returning `{"available": false, "source": "incois-erddap", "reason": "dataset unavailable"}` if server is degraded or out-of-bounds.

### 4.4 MET Norway (Weather Fallback)
- **Base URL**: `https://api.met.no`
- **Endpoint**: `/weatherapi/locationforecast/2.0/complete`
- **Identification**: Mandates descriptive `User-Agent` (`ORCA-SIH26176-Hackathon/1.0 (contact: student-team@sih26176.in)`).
- **Role**: Automatically invoked when Open-Meteo encounters a network timeout or HTTP 5xx error.

### 4.5 Copernicus Marine Service (CMEMS - Advanced Ocean)
- **Base URL**: `https://cq-cmems.copernicus.eu`
- **Authentication**: Registered credentials required (`COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD`).
- **Resilience**: If credentials are empty or `COPERNICUS_ENABLED=false`, the provider gracefully degrades to `credentials_missing` or `disabled` without crashing the application.

### 4.6 Tide Architecture & Sea-Level Distinction
- **Primary**: Open-Meteo Marine modeled sea level (`sea_level` above MSL).
- **Optional**: WorldTides (`https://www.worldtides.info/api/v3`) when `WORLDTIDES_ENABLED=true` and `WORLDTIDES_API_KEY` are provided.
- **Critical Maritime Labeling**: Open-Meteo sea level is numerical hydrodynamic ocean model output; it is explicitly labeled as `is_official_tide_table=False` and `datum="Mean Sea Level (MSL)"` to prevent confusion with official nautical chart datum harmonic predictions.

### 4.7 Nominatim Geocoder
- **Base URL**: `https://nominatim.openstreetmap.org`
- **Endpoints**: `/search` (forward), `/reverse` (coordinate resolution).
- **Rate Limit Policy**: Strictly throttled via token bucket at 1.0 request/second.
- **Coastal Bias**: Query selection prioritizes harbors, ports, piers, quays, and beaches over inland landmarks.

---

## 5. Potential Fishing Zone (PFZ) Distinction

India's marine advisory regulations require absolute transparency regarding fishing advisories:

| Feature | Official INCOIS PFZ | ORCA AI-Derived Candidate Fishing Zone |
| :--- | :--- | :--- |
| **Provider** | `OfficialINCOISPFZProvider` | `DerivedFishingZoneProvider` |
| **Data Source** | ESSO-INCOIS institutional bulletin | Oceanographic inference (SST, Chlorophyll, currents) |
| **`is_official_incois`** | `True` | `False` |
| **`zone_type`** | `"Official INCOIS PFZ"` | `"AI-derived candidate fishing zone"` |
| **Activation** | `INCOIS_OFFICIAL_ENABLED=true` + valid institutional API key | Active by default using real open oceanographic signals |
| **Algorithm** | Satellite composite + official validation | Frontal gradient analysis: SST 26–29.5°C optimal, Chlorophyll 0.3–2.5 mg/m³, current convergence |
| **Disclaimer** | None required | Mandatory scientific research disclaimer attached to every record |

---

## 6. Resilience, Fallback & Caching

### 6.1 Resilience Parameters
- `PROVIDER_TIMEOUT_SECONDS=15` (Fast responsiveness with per-query 6s budget for ERDDAP).
- `EXTERNAL_RETRY_ATTEMPTS=2`: Retries on connection resets or timeouts with exponential backoff (`min=1s`, `max=4s`).
- Circuit Breaker: Automatically trips open after 4 consecutive failures and enters half-open recovery after 30 seconds.

### 6.2 Caching Strategy
- Cache Keys use rounded coordinates to avoid unlimited fragmentation:
  - `orca:weather:{round(lat, 3)}:{round(lon, 3)}:{YYYYMMDDHH}` (TTL: 30 min)
  - `orca:marine:{round(lat, 3)}:{round(lon, 3)}:{YYYYMMDDHH}` (TTL: 30 min)
  - `orca:ocean:{round(lat, 3)}:{round(lon, 3)}:{YYYYMMDD}` (TTL: 60 min)
  - `orca:pfz:{round(lat, 3)}:{round(lon, 3)}:{YYYYMMDD}` (TTL: 4 hr)
  - `orca:tide:{round(lat, 3)}:{round(lon, 3)}:{YYYYMMDD}` (TTL: 60 min)
  - `orca:geocode:{normalized_name}` (TTL: 24 hr)
- Dual-tier: Valkey/Redis client when connected, with automatic process-level in-memory fallback.

### 6.3 Data Freshness Tagging
Every returned payload includes:
- `data_status`: `"fresh"`, `"stale"`, or `"unavailable"`
- `freshness_minutes`: elapsed minutes since observation timestamp
- `retrieved_at`: UTC timestamp of retrieval

---

## 7. Exposed REST API Endpoints

The Gateway exposes standard REST endpoints adhering to Section 18 & 19:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/marine/weather` | Atmospheric weather forecast (Open-Meteo -> MET Norway) |
| `GET` | `/api/marine/conditions` | Sea-state, waves, swell, currents, and SST |
| `GET` | `/api/marine/ocean` | Combined ocean state (chlorophyll-a & SST from INCOIS ERDDAP) |
| `GET` | `/api/marine/sst` | Sea Surface Temperature in Celsius |
| `GET` | `/api/marine/chlorophyll`| Chlorophyll-a concentration in mg/m³ |
| `GET` | `/api/marine/tide` | Water level and modeled sea-level elevation |
| `GET` | `/api/marine/fishing-zones` | PFZ advisories (Official INCOIS or AI-derived) |
| `GET` | `/api/marine/providers/status` | Operational status of all external providers |
| `GET` | `/api/marine/health` | Comprehensive Gateway health check |

### Backward-Compatible Endpoints Preserved:
- `GET /health`: Public container & gateway health
- `GET /weather/forecast`: Open-Meteo weather
- `GET /marine/forecast`: Open-Meteo marine wave forecast
- `GET /tide`: Harmonic tidal predictions
- `GET /fishing-zone/estimate`: Experimental suitability score
- `POST /safety/assess`: Deterministic maritime safety engine
- `POST /internal/ai/chat` & `/internal/v1/orca/execute`: LangGraph multi-agent pipeline

---

## 8. Environment Variables Reference

```env
# ==============================
# WEATHER
# ==============================
WEATHER_PROVIDER=open_meteo
WEATHER_BASE_URL=https://api.open-meteo.com
WEATHER_FORECAST_ENDPOINT=/v1/forecast

MET_NO_ENABLED=true
MET_NO_BASE_URL=https://api.met.no
MET_NO_ENDPOINT=/weatherapi/locationforecast/2.0/complete
MET_NO_USER_AGENT=ORCA-SIH26176-Hackathon/1.0 (contact: student-team@sih26176.in)

# ==============================
# MARINE
# ==============================
MARINE_PROVIDER=open_meteo
MARINE_BASE_URL=https://marine-api.open-meteo.com
MARINE_ENDPOINT=/v1/marine

# ==============================
# INCOIS ERDDAP
# ==============================
INCOIS_ERDDAP_ENABLED=true
INCOIS_ERDDAP_BASE_URL=https://erddap.incois.gov.in/erddap

# Official INCOIS API (Optional)
INCOIS_OFFICIAL_ENABLED=false
INCOIS_BASE_URL=
INCOIS_API_KEY=

# ==============================
# COPERNICUS MARINE (Optional)
# ==============================
COPERNICUS_ENABLED=false
COPERNICUS_USERNAME=
COPERNICUS_PASSWORD=

# ==============================
# TIDES
# ==============================
TIDE_PROVIDER=open_meteo
WORLDTIDES_ENABLED=false
WORLDTIDES_API_KEY=

# ==============================
# GEOCODING
# ==============================
GEOCODER_PROVIDER=nominatim
GEOCODER_BASE_URL=https://nominatim.openstreetmap.org
GEOCODER_ENDPOINT=/search

# ==============================
# PROVIDER RUNTIME
# ==============================
ENABLE_PROVIDER_FALLBACK=true
PROVIDER_TIMEOUT_SECONDS=15
EXTERNAL_RETRY_ATTEMPTS=2
MAX_DATA_FRESHNESS_MINUTES=360
```
