"""
Realistic Demo Marine Provider for ORCA (SIH26176).
Provides high-fidelity synthetic oceanographic datasets for Smart India Hackathon demonstrations
when external upstream APIs are down, rate-limited, or unconfigured.

CRITICAL: Every payload returned by this provider includes:
  "status": "DEMO DATA"
  "is_live": False
"""
import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from .base_provider import MarineDataProvider


class DemoMarineProvider(MarineDataProvider):
    """
    Simulates high-resolution oceanographic observation & forecast grids.
    Physically plausible models calibrated to the Arabian Sea and Bay of Bengal.
    """

    def __init__(self):
        super().__init__(name="ORCA Demo Marine Engine", is_live_source=False)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_base_coords(self, lat: Optional[float], lon: Optional[float], bbox: Optional[Tuple[float, float, float, float]]) -> Tuple[float, float]:
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            return (min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0
        return 18.98, 72.82  # Default Mumbai offshore

    async def get_sst(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        # Build a 5x5 grid of SST points around target area
        features: List[Dict[str, Any]] = []
        d_lat = 0.08
        d_lon = 0.08

        for i in range(-2, 3):
            for j in range(-2, 3):
                pt_lat = round(c_lat + i * d_lat, 4)
                pt_lon = round(c_lon + j * d_lon, 4)
                # Realistic gradient: cooler offshore/upwelling, warmer coastal shallows
                base_temp = 28.4 + 0.6 * math.sin(i * 0.8) - 0.4 * math.cos(j * 0.7)
                temp = round(base_temp, 2)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [pt_lon, pt_lat],
                    },
                    "properties": {
                        "variable": "sst",
                        "value": temp,
                        "unit": "°C",
                        "thermal_front": temp < 28.0,
                        "status": "DEMO DATA",
                        "source": "Demo Marine Provider (INCOIS Calibration Profile)",
                        "timestamp": timestamp,
                    }
                })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "sea_surface_temperature",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Provider (INCOIS Calibration Profile)",
                "unit": "°C",
                "min_sst": 27.4,
                "max_sst": 29.2,
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_chlorophyll(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        features: List[Dict[str, Any]] = []
        # Coastal upwelling plumes (higher productivity near 10-40m depth)
        for offset_x, offset_y, val, high_prod in [
            (-0.10, -0.05, 1.85, True),
            (-0.06, 0.02, 1.42, True),
            (0.00, -0.04, 1.65, True),
            (0.08, -0.10, 0.95, False),
            (-0.14, 0.08, 2.10, True),
            (0.12, 0.05, 0.68, False),
            (-0.02, 0.12, 1.25, True),
        ]:
            pt_lat = round(c_lat + offset_y, 4)
            pt_lon = round(c_lon + offset_x, 4)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt_lon, pt_lat],
                },
                "properties": {
                    "variable": "chlorophyll_a",
                    "value": val,
                    "unit": "mg/m³",
                    "upwelling_indicator": high_prod,
                    "productivity_zone": "High" if val > 1.2 else "Moderate",
                    "status": "DEMO DATA",
                    "source": "Demo Marine Provider (MODIS/OCM-3 Calibration Profile)",
                    "timestamp": timestamp,
                }
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "chlorophyll_a",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Provider (MODIS/OCM-3 Calibration Profile)",
                "unit": "mg/m³",
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_waves(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        features: List[Dict[str, Any]] = []
        for dy in [-0.12, 0.0, 0.12]:
            for dx in [-0.15, 0.0, 0.15]:
                pt_lat = round(c_lat + dy, 4)
                pt_lon = round(c_lon + dx, 4)
                wave_height = round(1.2 + 0.3 * math.sin(dx * 10), 2)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [pt_lon, pt_lat],
                    },
                    "properties": {
                        "variable": "waves",
                        "significant_wave_height_m": wave_height,
                        "dominant_period_s": 7.4,
                        "wave_direction_deg": 235,  # SW swell
                        "swell_height_m": 0.9,
                        "sea_state": "Slight to Moderate",
                        "status": "DEMO DATA",
                        "source": "Demo Marine Provider (ECMWF/WAM Profile)",
                        "timestamp": timestamp,
                    }
                })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "wave_height",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "significant_wave_height_m": 1.3,
                "sea_state": "Moderate",
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Provider (ECMWF/WAM Profile)",
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_wind(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        features: List[Dict[str, Any]] = []
        for dy in [-0.10, 0.0, 0.10]:
            for dx in [-0.12, 0.0, 0.12]:
                pt_lat = round(c_lat + dy, 4)
                pt_lon = round(c_lon + dx, 4)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [pt_lon, pt_lat],
                    },
                    "properties": {
                        "variable": "wind",
                        "wind_speed_knots": 14.5,
                        "wind_speed_kmh": 26.8,
                        "wind_direction_deg": 240,
                        "wind_gusts_knots": 18.2,
                        "beaufort_scale": 4,
                        "status": "DEMO DATA",
                        "source": "Demo Marine Provider (GFS/ICON Profile)",
                        "timestamp": timestamp,
                    }
                })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "wind",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "wind_speed_knots": 14.5,
                "wind_direction_deg": 240,
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Provider (GFS/ICON Profile)",
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_tides(
        self,
        lat: float,
        lon: float,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = self._now()
        # Semi-diurnal cycle simulation
        now_dt = datetime.now(timezone.utc)
        hour = now_dt.hour + now_dt.minute / 60.0
        # 12.4 hour lunar cycle approximation
        tidal_phase = (hour % 12.4) / 12.4 * 2.0 * math.pi
        tide_height = round(2.35 + 1.45 * math.sin(tidal_phase), 2)
        trend = "Rising (Flood Tide)" if math.cos(tidal_phase) > 0 else "Falling (Ebb Tide)"

        return {
            "status": "DEMO DATA",
            "is_live": False,
            "source": "Demo Marine Provider (Harmonic Port Constants)",
            "station": "Coastal Astronomical Reference",
            "latitude": lat,
            "longitude": lon,
            "current_height_m": tide_height,
            "trend": trend,
            "high_tide": {"height_m": 3.85, "time": "14:15 UTC"},
            "low_tide": {"height_m": 0.85, "time": "20:30 UTC"},
            "timestamp": timestamp,
        }

    async def get_pfz(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        # 3 realistic PFZ polygons where SST fronts meet chlorophyll upwelling
        poly1 = [
            [round(c_lon - 0.14, 4), round(c_lat - 0.04, 4)],
            [round(c_lon - 0.08, 4), round(c_lat + 0.03, 4)],
            [round(c_lon - 0.04, 4), round(c_lat - 0.01, 4)],
            [round(c_lon - 0.10, 4), round(c_lat - 0.07, 4)],
            [round(c_lon - 0.14, 4), round(c_lat - 0.04, 4)],
        ]
        poly2 = [
            [round(c_lon - 0.22, 4), round(c_lat + 0.06, 4)],
            [round(c_lon - 0.16, 4), round(c_lat + 0.12, 4)],
            [round(c_lon - 0.12, 4), round(c_lat + 0.08, 4)],
            [round(c_lon - 0.18, 4), round(c_lat + 0.02, 4)],
            [round(c_lon - 0.22, 4), round(c_lat + 0.06, 4)],
        ]

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [poly1],
                },
                "properties": {
                    "id": "pfz-alpha",
                    "name": "Primary Thermal Front (Zone Alpha)",
                    "type": "PFZ",
                    "confidence": 0.88,
                    "target_species": ["Mackerel", "Tuna", "Sardines"],
                    "sst_celsius": 27.8,
                    "chlorophyll_mg_m3": 1.74,
                    "distance_km": 16.4,
                    "bearing_deg": 245,
                    "depth_m": 35,
                    "advisory": "High pelagic fish aggregation along thermal-chlorophyll divergence edge.",
                    "status": "DEMO DATA",
                    "source": "Demo Marine Provider (INCOIS PFZ Model)",
                    "timestamp": timestamp,
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [poly2],
                },
                "properties": {
                    "id": "pfz-beta",
                    "name": "Offshore Upwelling Ridge (Zone Beta)",
                    "type": "PFZ",
                    "confidence": 0.81,
                    "target_species": ["Anchovy", "Carangids", "Ribbonfish"],
                    "sst_celsius": 28.1,
                    "chlorophyll_mg_m3": 1.48,
                    "distance_km": 24.1,
                    "bearing_deg": 280,
                    "depth_m": 48,
                    "advisory": "Productive shelf-edge gradient. Recommended for motorized gillnetters.",
                    "status": "DEMO DATA",
                    "source": "Demo Marine Provider (INCOIS PFZ Model)",
                    "timestamp": timestamp,
                }
            }
        ]

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "potential_fishing_zones",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "zone_count": len(features),
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Provider (INCOIS PFZ Model)",
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_risk(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        time: Optional[str] = None,
    ) -> Dict[str, Any]:
        c_lat, c_lon = self._get_base_coords(lat, lon, bbox)
        timestamp = self._now()

        # Nearshore reef / high-risk boundary
        high_risk_poly = [
            [round(c_lon - 0.03, 4), round(c_lat - 0.08, 4)],
            [round(c_lon + 0.01, 4), round(c_lat - 0.05, 4)],
            [round(c_lon + 0.02, 4), round(c_lat - 0.12, 4)],
            [round(c_lon - 0.02, 4), round(c_lat - 0.14, 4)],
            [round(c_lon - 0.03, 4), round(c_lat - 0.08, 4)],
        ]
        # Moderate risk open-swell corridor
        moderate_risk_poly = [
            [round(c_lon - 0.28, 4), round(c_lat - 0.15, 4)],
            [round(c_lon - 0.20, 4), round(c_lat - 0.05, 4)],
            [round(c_lon - 0.15, 4), round(c_lat - 0.18, 4)],
            [round(c_lon - 0.25, 4), round(c_lat - 0.22, 4)],
            [round(c_lon - 0.28, 4), round(c_lat - 0.15, 4)],
        ]

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [high_risk_poly],
                },
                "properties": {
                    "id": "hazard-shallow-shoal",
                    "level": "HIGH",
                    "color": "#EF4444",
                    "name": "Submerged Shoal & Heavy Surf Zone",
                    "hazard_type": "bathymetry_shoal",
                    "reason": "Water depth < 5m with breaking swell. Danger for all hull sizes.",
                    "status": "DEMO DATA",
                    "source": "Demo Marine Risk Engine",
                    "timestamp": timestamp,
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [moderate_risk_poly],
                },
                "properties": {
                    "id": "hazard-open-swell",
                    "level": "MODERATE",
                    "color": "#F59E0B",
                    "name": "Exposed Swell Corridor (2.2m Waves)",
                    "hazard_type": "wave_swell",
                    "reason": "Significant wave height 2.2m. Non-motorized crafts advised to avoid.",
                    "status": "DEMO DATA",
                    "source": "Demo Marine Risk Engine",
                    "timestamp": timestamp,
                }
            }
        ]

        return {
            "type": "FeatureCollection",
            "metadata": {
                "layer": "marine_risk_overlay",
                "center": {"latitude": c_lat, "longitude": c_lon},
                "overall_risk": "MODERATE",
                "status": "DEMO DATA",
                "is_live": False,
                "source": "Demo Marine Risk Engine",
                "timestamp": timestamp,
            },
            "features": features,
        }

    async def get_restricted_zones(
        self,
        center_lon: Optional[float] = None,
        center_lat: Optional[float] = None,
        radius_km: Optional[float] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Dict[str, Any]:
        try:
            from app.gis.spatial_engine import spatial_engine
            if spatial_engine:
                return spatial_engine.generate_zones_geojson(
                    center_lon=center_lon, center_lat=center_lat, radius_km=radius_km, bbox=bbox
                )
        except Exception:
            pass
        return {
            "type": "FeatureCollection",
            "features": [],
            "feature_count": 0,
            "generated_at": self._now(),
            "status": "DEMO DATA",
            "is_live": False,
        }

    async def get_overview(
        self,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        timestamp = self._now()
        return {
            "status": "DEMO DATA",
            "is_live": False,
            "source": "ORCA Multi-Layer Marine Engine",
            "coordinates": {"latitude": lat, "longitude": lon},
            "weather": {
                "temperature_c": 29.5,
                "wind_speed_knots": 14.2,
                "wind_direction_deg": 240,
                "visibility_km": 10.0,
                "condition": "Partly Cloudy",
            },
            "marine": {
                "significant_wave_height_m": 1.3,
                "dominant_period_s": 7.4,
                "sea_surface_temp_c": 28.3,
                "chlorophyll_mg_m3": 1.65,
                "tide_height_m": 2.4,
                "tide_state": "Rising",
            },
            "safety": {
                "risk_level": "LOWER",
                "recommendation": "SAFE_TO_FISH",
                "nearest_pfz_km": 16.4,
            },
            "timestamp": timestamp,
        }
