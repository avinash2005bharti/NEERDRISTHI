# Legal Licensing, Attribution & Data Governance

**ORCA: Marine Ecosystem Reasoning with Collaborative AI Agents**  
**Smart India Hackathon SIH26176**

ORCA strictly complies with open-data licenses, attribution mandates, intellectual property constraints, and maritime safety regulations.

---

## 1. Open Data Attribution Notices

### Open-Meteo Weather and Marine APIs
- **Licensing**: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Attribution Statement**:
  > *"Weather and marine sea-state forecast data provided courtesy of Open-Meteo.com under CC BY 4.0 license. Underlying meteorological models include ECMWF IFS, DWD ICON, and NOAA GFS/WaveWatch III."*
- **Terms of Service**: Non-commercial use permits up to 10,000 API calls per day without financial obligation.

### OpenStreetMap / Nominatim Geocoding
- **Licensing**: [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/)
- **Attribution Statement**:
  > *"Geographic place names and coastal coordinate lookups (c) OpenStreetMap contributors, licensed under the Open Database License (ODbL)."*
- **Compliance**:
  - All requests include a custom descriptive `User-Agent` header (`ORCA-SIH26176/1.0 contact@example.com`).
  - Public instance rate limit of 1 request/second is enforced by ORCA's internal `RateLimiter`.
  - Geocoding results are cached locally in Valkey and in-memory caches to prevent server exhaustion.

### NOAA CO-OPS Tides and Currents
- **Licensing**: U.S. Government Work / U.S. Public Domain.
- **Attribution Statement**:
  > *"Tidal prediction and water-level information derived from the National Oceanic and Atmospheric Administration (NOAA) Center for Operational Oceanographic Products and Services (CO-OPS)."*

### Local Indian Coastal Tide-Station Dataset
- **Licensing**: Open Data Commons Public Domain Dedication (PDDL) / Port Authority Published Benchmark Tables.
- **Attribution Statement**:
  > *"Astronomical tidal constituents and Chart Datum benchmarks compiled from published Survey of India and Major Port Authority tidal observatories (Mumbai, Chennai, Kochi, Visakhapatnam, Mormugao, Kandla)."*

### GDACS (Global Disaster Alert and Coordination System)
- **Licensing**: United Nations OCHA and European Commission Open Data Policy.
- **Attribution Statement**:
  > *"Disaster alerts and tropical cyclone coordinates provided by the Global Disaster Alert and Coordination System (GDACS), a joint initiative of the United Nations (UN OCHA) and the European Commission (DG ECHO / JRC)."*

### Local Satellite Demo Dataset
- **Licensing**: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Attribution Statement**:
  > *"Sample sea-surface temperature and chlorophyll-a values derived from Copernicus Marine Service (CMEMS) L4 analyzed SST and NASA OceanColor MODIS-Aqua L3 binned products. Attributed for offline algorithmic demonstrations."*

---

## 2. Regulatory & Safety Disclaimers

### Disclaimer 1: Experimental Decision Support Aid
> **IMPORTANT**: ORCA is an experimental decision-support and research platform developed for Smart India Hackathon SIH26176. It does **NOT** substitute for official government navigational or disaster warnings.

### Disclaimer 2: Prohibition on AI Emergency Claims
> **CRITICAL REQUIREMENT**: Never present an AI-generated fishing or safety recommendation as an official emergency warning. If severe threats (cyclones, gale winds, phenomenal sea states) are detected, ORCA generates a **Computed Risk Signal** and directs mariners to official authorities:
> - **India Meteorological Department (IMD)**: [https://mausam.imd.gov.in](https://mausam.imd.gov.in)
> - **Indian Coast Guard Search and Rescue (SAR)**: Emergency Toll-Free **1554** / VHF Channel 16
> - **National Disaster Management Authority (NDMA)**: Helpline **1070** / **112**

### Disclaimer 3: Potential Fishing Zone (PFZ) Research Estimate
> Sea-surface temperature (SST), chlorophyll-a, thermal front gradients, bathymetry, and wind-wave stability are **biological productivity indicators**, not guaranteed fish-location coordinates. ORCA results are termed **experimental fishing-zone suitability** or **research estimates**. They do not constitute an official INCOIS PFZ bulletin.
