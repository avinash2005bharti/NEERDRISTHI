# ORCA API Examples & Local Testing Commands

All endpoints can be tested locally using `curl` or tools like Postman / HTTPie.

Base URL: `http://localhost:8000`

---

## 1. Health & Provider Status

### Check System Health
```bash
curl -X GET "http://localhost:8000/health" -H "Accept: application/json"
```

**Response (Sample)**:
```json
{
  "status": "healthy",
  "service": "orca-agent-core",
  "role": "AI / LangGraph Multi-Agent & Spatial Intelligence Backend",
  "timestamp": "2026-09-27T12:00:00Z",
  "providers": {
    "weather": "configured",
    "marine": "configured",
    "geocoder": "configured",
    "tide": "configured",
    "valkey_cache": "unavailable"
  }
}
```

### List Registered Providers
```bash
curl -X GET "http://localhost:8000/providers"
```

---

## 2. Weather & Wind Forecast

### Query 3-day Weather Forecast for Mumbai Coastal Waters (18.98°N, 72.83°E)
```bash
curl -X GET "http://localhost:8000/weather/forecast?latitude=18.98&longitude=72.83&forecast_days=3"
```

**Response (Sample)**:
```json
{
  "status": "success",
  "data_status": "forecast",
  "provider": "Open-Meteo Weather API",
  "timestamp": "2026-09-27T12:00:00Z",
  "data": {
    "location": "Coordinates (18.980°N, 72.830°E)",
    "latitude": 18.98,
    "longitude": 72.83,
    "timezone": "Asia/Kolkata",
    "issued_at": "2026-09-27T12:00:00Z",
    "valid_from": "2026-09-27T12:00",
    "valid_to": "2026-09-30T11:00",
    "hourly_values": {
      "temperature_2m": [29.2, 29.5, 29.1],
      "wind_speed_10m": [5.8, 6.2, 5.4],
      "wind_direction_10m": [245, 250, 240],
      "wind_gusts_10m": [8.1, 8.9, 7.8],
      "precipitation": [0.0, 0.0, 0.4],
      "weather_code": [1, 2, 2],
      "surface_pressure": [1011.5, 1010.8, 1012.0],
      "visibility": [10000, 9500, 9000]
    },
    "units": {
      "temperature_2m": "°C",
      "wind_speed_10m": "m/s",
      "precipitation": "mm"
    },
    "confidence": 0.92
  },
  "attribution": {
    "source": "Open-Meteo",
    "url": "https://open-meteo.com",
    "license": "CC BY 4.0"
  }
}
```

---

## 3. Marine Waves & Sea State

### Query Marine Wave and Current Forecast
```bash
curl -X GET "http://localhost:8000/marine/forecast?latitude=18.98&longitude=72.83&forecast_days=3"
```

**Response (Sample)**:
```json
{
  "status": "success",
  "data_status": "forecast",
  "provider": "Open-Meteo Marine API",
  "timestamp": "2026-09-27T12:00:00Z",
  "data": {
    "location": "Offshore (18.980°N, 72.830°E)",
    "latitude": 18.98,
    "longitude": 72.83,
    "issued_at": "2026-09-27T12:00:00Z",
    "valid_from": "2026-09-27T12:00",
    "valid_to": "2026-09-30T11:00",
    "wave_height": 1.35,
    "wave_period": 7.1,
    "wave_direction": 262.0,
    "wind_speed": 4.8,
    "current_speed": 0.38,
    "current_direction": 175.0,
    "sea_level": 0.28,
    "units": {
      "wave_height": "m",
      "wave_period": "s",
      "wind_speed": "m/s",
      "current_speed": "m/s",
      "sea_level": "m"
    },
    "confidence": 0.88
  },
  "attribution": {
    "source": "Open-Meteo Marine API",
    "url": "https://marine-api.open-meteo.com",
    "license": "CC BY 4.0"
  }
}
```

---

## 4. Tide & Water Level

### A. Coastal Station Query (Within 150 km of Mumbai)
```bash
curl -X GET "http://localhost:8000/tide?latitude=18.98&longitude=72.83"
```

**Response (Sample)**:
```json
{
  "status": "success",
  "data_status": "prediction",
  "provider": "Local-Tide-Station-Dataset",
  "timestamp": "2026-09-27T12:00:00Z",
  "data": {
    "station": "Mumbai (Apollo Bunder / Sassoon Docks)",
    "station_id": "IN-MUM-01",
    "observed_or_predicted": "predicted",
    "timestamp": "2026-09-27T12:00:00Z",
    "water_level": 2.45,
    "datum": "Chart Datum (CD)",
    "units": "meters",
    "provider": "Local-Tide-Station-Dataset",
    "source_url": "https://mumbaiport.gov.in",
    "data_status": "prediction",
    "confidence": 0.88
  },
  "attribution": {
    "source": "Local-Tide-Station-Dataset",
    "url": "local://data/tide/tide_stations.json",
    "notice": "Tidal prediction relative to Chart Datum (CD)."
  }
}
```

### B. Deep Ocean Query (No Configured Tide Provider)
```bash
curl -X GET "http://localhost:8000/tide?latitude=0.0&longitude=70.0"
```

**Response (DATA_UNAVAILABLE)**:
```json
{
  "status": "DATA_UNAVAILABLE",
  "category": "tide",
  "data_status": "DATA_UNAVAILABLE",
  "reason": "No configured tide provider for this location",
  "data": null,
  "provider": "none",
  "timestamp": "2026-09-27T12:00:00Z"
}
```

---

## 5. Potential Fishing Zone (PFZ) Suitability

### Query Experimental PFZ Suitability Estimate
```bash
curl -X GET "http://localhost:8000/fishing-zone/estimate?latitude=18.98&longitude=72.83"
```

**Response (Sample)**:
```json
{
  "status": "success",
  "data": {
    "location": {
      "latitude": 18.98,
      "longitude": 72.83
    },
    "suitability_score": 0.78,
    "category": "experimental fishing-zone suitability",
    "confidence": 0.68,
    "contributing_variables": {
      "sea_surface_temperature_celsius": 28.4,
      "sst_suitability_index": 0.90,
      "chlorophyll_a_mg_m3": 1.45,
      "chlorophyll_suitability_index": 0.88,
      "wave_stability_factor": 1.0,
      "estimated_bathymetry_depth_meters": 24.0,
      "estimated_distance_from_coast_km": 14.5,
      "thermal_front_gradient": "Moderate oceanographic thermal boundary detected"
    },
    "indicators_disclaimer": "DISCLAIMER: This is an experimental oceanographic research estimate. Sea-surface temperature (SST), chlorophyll-a, bathymetry, distance from coast, and weather are biological productivity indicators, NOT a guaranteed fish-location prediction. This does NOT represent an official INCOIS Potential Fishing Zone (PFZ) advisory.",
    "timestamp": "2026-09-27T12:00:00Z",
    "provider": "ORCA Experimental PFZ Reasoning Engine (Open-Data Mode)"
  },
  "timestamp": "2026-09-27T12:00:00Z"
}
```

---

## 6. Deterministic Safety Assessment (Multilingual)

### Assess Fishermen Safety for Motorized Fiberglass Boat in Hindi
```bash
curl -X POST "http://localhost:8000/safety/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 18.98,
    "longitude": 72.83,
    "vessel_class": "motorized_fiberglass",
    "language": "hi"
  }'
```

**Response (Sample)**:
```json
{
  "status": "success",
  "assessment": {
    "decision": "GO",
    "risk_score": 15,
    "risk_level": "LOW",
    "valid_time": "2026-09-27T12:00:00Z",
    "location": {
      "latitude": 18.98,
      "longitude": 72.83
    },
    "reasons": [
      "All weather and sea-state parameters within safe limits for FRP Motorized Fishing Boat (< 10m)."
    ],
    "weather_evidence": {
      "wind_speed": 5.8,
      "provider": "Open-Meteo Weather API"
    },
    "marine_evidence": {
      "wave_height": 1.35,
      "wave_period": 7.1,
      "provider": "Open-Meteo Marine API"
    },
    "tide_evidence": {
      "water_level": 2.45,
      "station": "Mumbai (Apollo Bunder / Sassoon Docks)"
    },
    "alert_evidence": [],
    "missing_data": [],
    "official_sources": [
      "Open-Meteo Weather API",
      "Open-Meteo Marine API",
      "Local-Tide-Station-Dataset"
    ],
    "disclaimer": "SAFETY ADVISORY NOTICE: This assessment is an automated, algorithmic decision-support tool. Never present an AI-generated fishing or safety recommendation as an official emergency warning. Always follow mandatory orders issued by the India Meteorological Department (IMD), National Disaster Management Authority (NDMA), and Indian Coast Guard. Emergency SAR Helpline: 1554 / VHF Ch 16.",
    "generated_at": "2026-09-27T12:00:00Z",
    "explanations": {
      "en": "ORCA Safety Assessment: [GO] for FRP Motorized Fishing Boat (< 10m). Risk Level: LOW (Score: 15/100). All weather and sea-state parameters within safe limits. Emergency contacts: Coast Guard 1554, VHF Channel 16.",
      "hi": "ओरका (ORCA) समुद्री सुरक्षा निर्णय: [प्रस्थान सुरक्षित (GO)]। नाव प्रकार: FRP Motorized Fishing Boat (< 10m)। जोखिम स्तर: LOW (अंक: 15/100)। प्रमुख कारण: सभी मौसम और समुद्री पैरामीटर सुरक्षित सीमा में हैं। आपातकालीन संपर्क: भारतीय तटरक्षक बल (Coast Guard) टोल-फ्री 1554 या वीएचएफ चैनल 16।",
      "mr": "ओर्का (ORCA) सागरी सुरक्षा निकाल: [प्रवासास अनुमती (GO)]। बोटीचा प्रकार: FRP Motorized Fishing Boat (< 10m)। धोक्याची पातळी: LOW (गुण: 15/100)। कारणे: सर्व हवामान व सागरी लाटांचे प्रमाण सुरक्षित मर्यादेत आहे. तातडीचा संपर्क: भारतीय तटरक्षक दल (Indian Coast Guard) 1554 किंवा व्हीएचएफ चॅनेल 16."
    }
  },
  "timestamp": "2026-09-27T12:00:00Z"
}
```
