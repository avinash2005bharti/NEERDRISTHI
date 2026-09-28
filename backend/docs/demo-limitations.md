# ORCA Demo Mode, System Limitations & Production Roadmap

**Problem Statement**: SIH26176 — Marine Ecosystem Reasoning with Collaborative AI Agents  
**Document**: Demo Architecture & Known Operational Boundaries

---

## 1. Demo Mode vs. Production Mode

ORCA features a dedicated `DEMO_MODE=true` toggle in `.env`. When active:
- High-fidelity **open-data APIs** requiring zero API keys (Open-Meteo Weather, Open-Meteo Marine, Nominatim Geocoding, GDACS Alerts) are used directly for live forecast queries.
- Regions requiring restricted governmental credentials or complex satellite pipeline subscriptions degrade safely to **attributed, local benchmark datasets** (`app/data/satellite/satellite_demo.json` and `app/data/tide/tide_stations.json`).

| Component | In Demo Mode (`DEMO_MODE=true`) | In Production (`DEMO_MODE=false`) |
|---|---|---|
| **Weather & Wind** | Open-Meteo free tier (< 10,000 req/day) | Open-Meteo commercial API key or NOAA/ECMWF pipeline |
| **Marine Waves** | Open-Meteo Marine free tier | Open-Meteo commercial or Copernicus Marine (CMEMS) WAV |
| **Geocoding** | Nominatim Public (rate-limited 1 req/s) | Self-hosted Nominatim Docker instance |
| **Tide & Water Level** | Local coastal station dataset (harmonic tables) | Real-time radar/acoustic tide gauge telemetry or official API |
| **Satellite SST & Chl-a** | Attributed offline benchmark sample | Live Copernicus Marine Service or NASA Earthdata API token |
| **Cyclone Alerts** | GDACS open RSS + Computed Risk Signals | IMD official XML/CAP alert gateway + GDACS |
| **Safety Engine** | Deterministic physical rule evaluation | Deterministic physical rule evaluation + Harbor Master feeds |

---

## 2. Key Limitations & Assumptions

### Limitation 1: Satellite Data Non-Live In Demo Mode
- **Rationale**: Satellite ocean-color (Chlorophyll-a) and high-resolution Level-4 SST data from Copernicus and NASA Earthdata require active registered credentials, multi-gigabyte NetCDF downloading, and OPeNDAP pipeline configuration.
- **Handling**: In demo mode, ORCA serves verified benchmark samples from `app/data/satellite/satellite_demo.json`.
- **Transparency**: Every response is explicitly tagged `data_status="demo"`, exposing the dataset timestamp and license. **Demo data is never presented as live observations.**

### Limitation 2: Tide Coverage Beyond 150 km From Coastal Gauges
- **Rationale**: Coastal astronomical tides depend heavily on bathymetry and local harbor amphidromic points. Global numerical models without high-resolution bathymetric grids introduce substantial error.
- **Handling**: If coordinates are further than 150 km from an Indian port tide station (e.g., in the middle of the Indian Ocean), ORCA cascades to the nearby water-level proxy or returns `status="DATA_UNAVAILABLE"`, `reason="No configured tide provider for this location"`.
- **Transparency**: ORCA **never substitutes wave height for tide height**.

### Limitation 3: Potential Fishing Zone (PFZ) Disclaimer
- **Rationale**: Official INCOIS PFZ bulletins combine high-resolution satellite thermal fronts, chlorophyll blooms, and oceanographic convergence models with proprietary bathymetry and seasonal migration data.
- **Handling**: In open-data demo mode, ORCA terms the output **“experimental fishing-zone suitability”** or **“research estimate”**.
- **Transparency**: The response clearly explains that SST, chlorophyll, bathymetry, and weather are environmental suitability indicators, **not a guaranteed fish-location prediction**.

### Limitation 4: Public Geocoding Rate Limits
- **Rationale**: The OpenStreetMap Nominatim public server imposes an absolute rate limit of 1 request per second and prohibits bulk geocoding.
- **Handling**: ORCA enforces an internal token-bucket `RateLimiter` and aggressive memory/Valkey caching. For high-volume load testing, self-hosting Nominatim via Docker is required.

---

## 3. Transitioning to Full Production Deployment

1. **Deploy Self-Hosted Nominatim**:
   Set `GEOCODER_BASE_URL=http://your-nominatim-host:8080` in `.env` to eliminate the 1 req/s rate limit.
2. **Obtain Copernicus Marine Credentials**:
   Register at `marine.copernicus.eu` and configure `SATELLITE_API_KEY`.
3. **Connect Official Port/MoES Data**:
   When granted institutional clearance for IMD/INCOIS APIs, supply `INCOIS_BASE_URL`, `INCOIS_API_KEY`, `ALERT_BASE_URL`, and `ALERT_API_KEY`.
4. **Set Production Mode**:
   Set `APP_ENV=production` and `DEMO_MODE=false`.
