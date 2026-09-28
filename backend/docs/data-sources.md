# ORCA Marine Intelligence — Data Sources & Open Data Registry

**Project**: ORCA (Smart India Hackathon SIH26176)  
**Topic**: Marine Ecosystem Reasoning with Collaborative AI Agents  
**Architecture**: Pluggable Open-Data Provider Abstraction Layer

This document catalogs every external and internal data source integrated into ORCA. It explicitly distinguishes between open-source software, open data, free APIs, free tiers, commercial APIs, restricted government APIs, and self-hostable datasets.

---

## 1. Provider Classification Matrix

| Provider Name | Domain / Role | Category Type | Auth Required? | Free / Open? | Production Ready? | Fallback Provider |
|---|---|---|---|---|---|---|
| **Open-Meteo Weather** | Atmospheric weather & wind | Open Data / Free API | No | Free (CC BY 4.0) | Yes (< 10k req/day or commercial tier) | NOAA GFS / ECMWF |
| **Open-Meteo Marine** | Waves, swell, sea-state, currents | Open Data / Free API | No | Free (CC BY 4.0) | Yes (< 10k req/day or commercial tier) | Copernicus Marine / NOAA WaveWatch |
| **Nominatim (OSM)** | Geocoding & Reverse Geocoding | Open Data / Self-hostable | No | Free (ODbL) | Yes (Self-hosted for high-volume) | Photon (Komoot) |
| **Local Tide Dataset** | Coastal tide predictions | Self-hostable Dataset | No | Free (Open Data Commons) | Yes (Major Indian ports) | Open-Meteo Sea Level Proxy |
| **NOAA CO-OPS** | Tide predictions & observations | Open Data / Free API | No | Free (Public Domain) | Yes (Supported stations) | Local Tide Dataset |
| **GDACS Alerts** | Tropical cyclone & disaster alerts | Open Data (UN/EC) | No | Free (Open Access) | Yes | Computed Risk Signals |
| **Computed Risk Signals** | Rule-based meteorological signals | Open Source Software | No | Free (Built-in) | Yes (Advisory only) | IMD Official Portal |
| **Local Satellite Demo** | Benchmark SST & Chlorophyll-a | Self-hostable Dataset | No | Free (CC BY 4.0) | Demo / Offline only | Copernicus / NASA |
| **Copernicus Marine** | Satellite SST & Chlorophyll-a | Open Data (Reg. Required)| Yes (Free Account)| Free for research / operational | Yes (Requires API token) | Local Demo Dataset |
| **NASA Earthdata** | Satellite MODIS/VIIRS Ocean Color | Open Data (Reg. Required)| Yes (Earthdata Login) | Free (Public NASA policy) | Yes (Requires bearer token) | Local Demo Dataset |
| **NOAA CoastWatch ERDDAP** | Gridded oceanographic variables | Open Data Protocol | No | Free (Public Domain) | Yes | Local Demo Dataset |
| **IMD Official Portal** | Cyclone bulletins & port warnings | Restricted Gov API | Yes (MoES Requisition)| Restricted Gov Access | Requires institutional clearance | GDACS / Computed Risk Signals |
| **INCOIS Official Portal**| Official PFZ & Ocean State Forecast| Restricted Gov API | Yes (Requisition Form) | Restricted Gov Access | Requires data requisition form | Open-Meteo Marine / Local Demo |

---

## 2. Detailed Provider Specifications

### A. Open-Meteo Weather API
- **Official Website**: [https://open-meteo.com](https://open-meteo.com)
- **API Base URL**: `https://api.open-meteo.com`
- **Primary Endpoint**: `GET /v1/forecast`
- **Classification**: **Open Data / Free API** (Commercial tier available from Open-Meteo GmbH)
- **Authentication**: None required for non-commercial demo usage.
- **Rate Limits**: 10,000 API calls per day, max 10 requests per second on the free tier.
- **License / Attribution**: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Geographic Coverage**: Global, seamless 0.1° (~11 km) gridded resolution using ECMWF IFS, DWD ICON, and GFS models.
- **Update Frequency**: Hourly operational forecast updates.
- **Data Status**: `forecast` (with hourly historical observations for the past 2 days).
- **Variables Supported**:
  - `temperature_2m` (°C)
  - `relative_humidity_2m` (%)
  - `precipitation` (mm)
  - `rain` (mm)
  - `weather_code` (WMO code)
  - `cloud_cover` (%)
  - `surface_pressure` (hPa)
  - `wind_speed_10m` (m/s)
  - `wind_direction_10m` (degrees)
  - `wind_gusts_10m` (m/s)
  - `visibility` (meters)
- **Production Suitability**: Suitable for production. For high-volume enterprise traffic (> 10k req/day), an API key from Open-Meteo can be supplied via `WEATHER_API_KEY`.
- **Fallback Behaviour**: If unreachable or timed out after exponential retries, cascades to NOAA GFS or returns `DATA_UNAVAILABLE`.

---

### B. Open-Meteo Marine API
- **Official Website**: [https://open-meteo.com/en/docs/marine-weather-api](https://open-meteo.com/en/docs/marine-weather-api)
- **API Base URL**: `https://marine-api.open-meteo.com` (Configurable independently via `MARINE_BASE_URL`)
- **Primary Endpoint**: `GET /v1/marine`
- **Classification**: **Open Data / Free API**
- **Authentication**: None required for demo tier.
- **Rate Limits**: 10,000 calls per day.
- **License / Attribution**: Creative Commons Attribution 4.0 International (CC BY 4.0). Derived from ECMWF WAM, NOAA WaveWatch III, and DWD models.
- **Geographic Coverage**: Global oceans and seas (5 km coastal resolution, 25 km open ocean).
- **Update Frequency**: Every 6 hours.
- **Data Status**: `forecast`.
- **Variables Supported**:
  - `wave_height` (significant wave height in meters)
  - `wave_direction` (degrees)
  - `wave_period` (seconds)
  - `wind_wave_height` (meters)
  - `wind_wave_direction` (degrees)
  - `wind_wave_period` (seconds)
  - `swell_wave_height` (meters)
  - `swell_wave_direction` (degrees)
  - `swell_wave_period` (seconds)
  - `ocean_current_velocity` (m/s)
  - `ocean_current_direction` (degrees)
  - `sea_level` (meters anomaly, where supported)
- **Production Suitability**: Production ready.
- **Fallback Behaviour**: Falls back to Copernicus Marine or returns `DATA_UNAVAILABLE`.

---

### C. Nominatim / OpenStreetMap Geocoder
- **Official Website**: [https://nominatim.openstreetmap.org](https://nominatim.openstreetmap.org)
- **Base URL**: `https://nominatim.openstreetmap.org` (Configurable via `GEOCODER_BASE_URL` for self-hosted instances)
- **Endpoints**: `GET /search` (forward geocoding), `GET /reverse` (reverse geocoding)
- **Classification**: **Open Data / Self-Hostable Software**
- **Authentication**: None required.
- **OSM Usage Policy Requirements**:
  1. Mandatory descriptive `User-Agent` header containing application name and contact email (`GEOCODER_USER_AGENT`).
  2. Strict rate limit: **Max 1 request per second** on the public instance. Enforced by ORCA's internal `RateLimiter`.
  3. Caching of repeated queries in memory and Valkey/Redis.
- **License / Attribution**: Open Database License (ODbL) by the OpenStreetMap Foundation (OSMF). (c) OpenStreetMap contributors.
- **Geographic Coverage**: Worldwide coastal villages, harbors, jetties, fishing landing centers, and ports.
- **Production Suitability**: The public instance is for low-volume development/demo. For high-volume production, deploy a self-hosted Nominatim Docker container and set `GEOCODER_BASE_URL`.
- **Fallback Behaviour**: Falls back to Photon (Komoot) or algorithmic coordinate validation.

---

### D. Coastal Tide Station Dataset & NOAA CO-OPS
- **Order of Execution**:
  1. **Configurable Official Tide Provider**: Activated if `TIDE_BASE_URL` and `TIDE_ENDPOINT` are supplied.
  2. **NOAA CO-OPS Tides API**: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter` (U.S. Public Domain, free).
  3. **FES / TPXO Global Tide Models**: Finite Element Solution hydrodynamic tidal grid data.
  4. **Local Tide-Station Dataset**: Package data located at `app/data/tide/tide_stations.json`. Contains harmonic tidal constituents (M2, S2, MSL) and Chart Datum benchmarks for major Indian ports (Mumbai Sassoon Docks, Chennai, Kochi, Visakhapatnam, Mormugao, Kandla).
  5. **Nearby Water-Level Proxy**: Derived from Open-Meteo `sea_level` anomaly. Explicitly flagged as `observed_or_predicted="estimated"`.
- **Classification**: Self-hostable dataset + Open Data API.
- **Attribution**: Survey of India Tidal Observatories & Port Authorities / NOAA CO-OPS.
- **Safety Invariant**: If no tide source exists within 150 km, returns `status="DATA_UNAVAILABLE"`, `reason="No configured tide provider for this location"`. **Never substitutes wave height for tide height.**

---

### E. Satellite Ocean Color & Sea Surface Temperature (SST)
- **1. Local Demo Mode**:
  - Dataset: `app/data/satellite/satellite_demo.json`
  - Variables: `sea_surface_temperature` (°C), `chlorophyll_a` (mg/m³), bathymetry (m), coastal distance (km).
  - Classification: **Self-hostable Benchmark Dataset**.
  - **Invariant**: Strictly labeled `data_status="demo"`. Exposes dataset timestamp and license. Never claims to be live.
- **2. Copernicus Marine Service (CMEMS)**:
  - Products: `SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001` (SST), `OCEANCOLOUR_GLO_BGC_L3_NRT_009_101` (Chlorophyll-a).
  - Registration: Free account at [marine.copernicus.eu](https://marine.copernicus.eu).
  - Set `SATELLITE_API_KEY` in `.env`.
- **3. NASA Earthdata OceanColor**:
  - Products: MODIS-Aqua L3 Daily Chlorophyll-a / VIIRS SST.
  - Registration: Free account at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov).
- **4. NOAA CoastWatch ERDDAP**:
  - Base URL: `https://coastwatch.pfeg.noaa.gov/erddap`
  - Open data protocol, accessible via REST.

---

### F. Cyclone & Severe Weather Alerts
- **1. GDACS (Global Disaster Alert and Coordination System)**:
  - URL: `https://www.gdacs.org/xml/rss.xml`
  - Classification: **Open Data** (United Nations OCHA & European Commission).
  - Event Types: Tropical Cyclones, Tsunamis, Storm Surges.
  - Auth: None required.
- **2. Computed Risk Signals**:
  - Algorithmic evaluation of physical variables: wind speed ≥ 17.5 m/s (gale force), wave height ≥ 3.5m, thunderstorm codes.
  - **Invariant**: Described as a computed mathematical signal. Prominently directs the user to official authorities (IMD, Coast Guard SAR Helpline 1554 / VHF Ch 16).
- **3. India Meteorological Department (IMD)**:
  - Classification: **Restricted Government API**.
  - Official access requires application to Ministry of Earth Sciences (MoES).
