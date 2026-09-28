# ORCA Marine Data Architecture & Provider Gateway (SIH26176)

Please refer to the primary project documentation at:
[`docs/MARINE_DATA_ARCHITECTURE.md`](../../docs/MARINE_DATA_ARCHITECTURE.md)

This architecture establishes a centralized **Marine Data Gateway** (`MarineDataGateway`) for ORCA, coordinating:
1. Open-Meteo Weather API (Primary Atmospheric)
2. MET Norway Locationforecast/2.0 (Automatic Weather Fallback)
3. Open-Meteo Marine API (Primary Waves, Swell, SST, Currents, Sea Level)
4. INCOIS ERDDAP (Verified Chlorophyll & SST Datasets)
5. Copernicus Marine Service (CMEMS Advanced Ocean Physics)
6. Open-Meteo Marine Modeled Sea Level <-> WorldTides
7. Nominatim OpenStreetMap (Coastal Geocoder with Rate Limiting)
8. Official INCOIS PFZ (Institutional) <-> ORCA AI-Derived Candidate Fishing Zones
