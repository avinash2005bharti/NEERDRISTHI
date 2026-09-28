# ORCA Provider Setup & Configuration Guide

**Problem Statement**: SIH26176 — Marine Ecosystem Reasoning with Collaborative AI Agents  
**Target Environment**: Development / Open-Data Hackathon Demonstration / Self-Hosted Production

This guide explains how to configure, test, and swap external data providers in ORCA.

---

## 1. Quickstart: 100% Zero-API-Key Demo Setup

ORCA is pre-configured to run out of the box with zero paid API keys:

1. **Weather**: Uses Open-Meteo Weather API (`WEATHER_PROVIDER=open_meteo`). Free open data, no registration required.
2. **Marine Sea State**: Uses Open-Meteo Marine API (`MARINE_PROVIDER=open_meteo`). Free open data, no key required.
3. **Coastal Geocoding**: Uses Nominatim / OpenStreetMap (`GEOCODER_PROVIDER=nominatim`). Free open data, rate-limited to 1 req/sec.
4. **Tide & Water Levels**: Uses local coastal tide-station dataset (`TIDE_PROVIDER=local_dataset`). Contains verified harmonic constants for Indian ports.
5. **Satellite SST & Chlorophyll-a**: Uses local benchmark demo dataset (`SATELLITE_PROVIDER=demo`). Attributed sample data for research.
6. **Cyclone Alerts**: Uses GDACS (`ALERT_PROVIDER=gdacs`) and internal computed risk signals. Free open feed.

### Setup Steps
```bash
# 1. Navigate to the agent-core backend
cd backend/ai-services

# 2. Copy the template environment file
cp .env.example .env

# 3. Create a Python 3.12 virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the FastAPI development server
python main.py
# The server starts at http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

---

## 2. Environment Variables Configuration

Copy `.env.example` to `.env`. Ensure that `.env` is never committed to Git.

```ini
# Core Configuration
APP_ENV=development
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
LOG_LEVEL=INFO

# Provider Selection
WEATHER_PROVIDER=open_meteo
WEATHER_BASE_URL=https://api.open-meteo.com

MARINE_PROVIDER=open_meteo
MARINE_BASE_URL=https://marine-api.open-meteo.com

GEOCODER_PROVIDER=nominatim
GEOCODER_BASE_URL=https://nominatim.openstreetmap.org
GEOCODER_USER_AGENT=ORCA-SIH26176/1.0 contact@example.com

TIDE_PROVIDER=local_dataset
SATELLITE_PROVIDER=demo
ALERT_PROVIDER=gdacs

# Resilience & Timeouts
REQUEST_TIMEOUT_SECONDS=30
EXTERNAL_RETRY_ATTEMPTS=3
MAX_DATA_FRESHNESS_MINUTES=360
CACHE_TTL_SECONDS=900
DEMO_MODE=true
```

---

## 3. Connecting Registered & Institutional Providers

### A. Copernicus Marine Service (CMEMS)
1. Register for a free institutional/scientific account at [https://marine.copernicus.eu/](https://marine.copernicus.eu/).
2. Obtain your API credentials or CAS personal access token.
3. Update `.env`:
   ```ini
   SATELLITE_PROVIDER=copernicus
   SATELLITE_BASE_URL=https://cq-cmems.copernicus.eu
   SATELLITE_API_KEY=your_copernicus_token_here
   SATELLITE_DATASET=SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001
   ```

### B. NASA Earthdata (OceanColor)
1. Register at NASA Earthdata Login: [https://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/).
2. Generate an Earthdata User Token.
3. Update `.env`:
   ```ini
   SATELLITE_PROVIDER=nasa
   SATELLITE_API_KEY=your_nasa_earthdata_token_here
   ```

### C. Self-Hosted Nominatim Geocoder (For High Throughput)
1. Launch Nominatim with Docker:
   ```bash
   docker run -d --name nominatim -p 8080:8080 mediagis/nominatim:4.4
   ```
2. Update `.env`:
   ```ini
   GEOCODER_BASE_URL=http://localhost:8080
   GEOCODER_RATE_LIMIT_PER_SECOND=20
   ```

### D. Official Indian Ocean Telemetry (IMD / INCOIS)
1. Official access to IMD and INCOIS REST endpoints requires formal requisition via the Ministry of Earth Sciences (MoES):
   - IMD: Apply at [https://api.imd.gov.in](https://api.imd.gov.in) (Contact: `sankar.nath@imd.gov.in`)
   - INCOIS: Submit Data Requisition Form to `uday@incois.gov.in` / `osf@incois.gov.in`.
2. Once credentials are provided, configure:
   ```ini
   ALERT_PROVIDER=imd
   ALERT_BASE_URL=https://api.imd.gov.in
   ALERT_API_KEY=your_imd_api_key_here

   INCOIS_BASE_URL=https://incois.gov.in/portal
   INCOIS_API_KEY=your_incois_token_here
   ```
3. If unconfigured, ORCA safely degrades to open data (Open-Meteo, GDACS, local datasets) and clearly marks the missing feeds.
