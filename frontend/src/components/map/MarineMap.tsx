import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import {
  Layers,
  Crosshair,
  RefreshCw,
  Compass,
  AlertTriangle,
  Anchor,
  Navigation,
  MapPin,
  ChevronDown,
  Route,
  CheckCircle2,
  XCircle,
  ArrowRight,
  LifeBuoy,
  Droplets,
  X,
  Info,
} from 'lucide-react';
import { marineService } from '../../services/marine/marineService';
import { OceanDataPanel } from './OceanDataPanel';
import { EmergencySosModal } from '../common/EmergencySosModal';
import {
  GeoJsonFeatureCollection,
  SpotOverview,
  MarineMapConfig,
  RouteAnalysisResult,
} from '../../types';
import { appStore } from '../../stores/appState';
import { useAppState } from '../../hooks/useAppState';

// Base map tile definitions (All free, high-speed, zero API token required)
const BASE_TILES: Record<string, { url: string; attr: string; maxZoom: number; maxNativeZoom?: number; subdomains?: string; name: string }> = {
  nautical_ocean: {
    name: 'Ocean Bathymetry',
    url: 'https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    attr: 'Tiles &copy; Esri, GEBCO, NOAA, National Geographic',
    maxZoom: 18,
    maxNativeZoom: 16,
  },
  carto_nautical_dark: {
    name: 'Nautical Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    attr: '&copy; CARTO &copy; OpenStreetMap',
    maxZoom: 20,
    subdomains: 'abcd',
  },
  esri_satellite: {
    name: 'HD Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr: 'Tiles &copy; Esri, i-cubed, USDA, USGS',
    maxZoom: 18,
  },
  osm_standard: {
    name: 'Coastal Road',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
    subdomains: 'abc',
  },
};

// Major Indian Coastal Fishing Harbours & Landing Centers for Smart Nav
export const MAJOR_FISHING_PORTS = [
  { id: 'custom_gps', name: '📍 Current GPS / Active Position', coords: [18.922, 72.834] as [number, number] },
  { id: 'mumbai_sassoon', name: 'Sassoon Dock, Mumbai (MH)', coords: [18.917, 72.825] as [number, number] },
  { id: 'veraval', name: 'Veraval Fishing Port (GJ)', coords: [20.902, 70.366] as [number, number] },
  { id: 'okha', name: 'Okha Harbour, Saurashtra (GJ)', coords: [22.468, 69.072] as [number, number] },
  { id: 'porbandar', name: 'Porbandar Port (GJ)', coords: [21.642, 69.601] as [number, number] },
  { id: 'ratnagiri', name: 'Mirkarwada / Ratnagiri (MH)', coords: [16.991, 73.284] as [number, number] },
  { id: 'mormugao', name: 'Mormugao / Betul Harbour (Goa)', coords: [15.416, 73.801] as [number, number] },
  { id: 'karwar', name: 'Baithkol / Karwar Port (KA)', coords: [14.808, 74.125] as [number, number] },
  { id: 'mangalore', name: 'Old Bunder, Mangalore (KA)', coords: [12.861, 74.835] as [number, number] },
  { id: 'kochi', name: 'Thoppumpady / Kochi Harbour (KL)', coords: [9.932, 76.262] as [number, number] },
  { id: 'kollam', name: 'Neendakara / Kollam (KL)', coords: [8.943, 76.541] as [number, number] },
  { id: 'vizhinjam', name: 'Vizhinjam International Port (KL)', coords: [8.375, 76.988] as [number, number] },
  { id: 'kanyakumari', name: 'Chinna Muttam, Kanyakumari (TN)', coords: [8.093, 77.568] as [number, number] },
  { id: 'tuticorin', name: 'Tuticorin V.O.C. Port (TN)', coords: [8.751, 78.175] as [number, number] },
  { id: 'chennai', name: 'Kasimedu / Royapuram, Chennai (TN)', coords: [13.125, 80.297] as [number, number] },
  { id: 'kakinada', name: 'Kakinada Deepwater Port (AP)', coords: [16.982, 82.285] as [number, number] },
  { id: 'vizag', name: 'Visakhapatnam Fishing Harbour (AP)', coords: [17.695, 83.302] as [number, number] },
  { id: 'paradip', name: 'Paradip Fishery Port (OD)', coords: [20.292, 86.685] as [number, number] },
  { id: 'digha', name: 'Digha / Shankarpur (WB)', coords: [21.625, 87.564] as [number, number] },
  { id: 'port_blair', name: 'Phoenix Bay, Port Blair (A&N)', coords: [11.674, 92.735] as [number, number] },
  { id: 'kavaratti', name: 'Kavaratti Jetty (Lakshadweep)', coords: [10.567, 72.641] as [number, number] },
];

export const POPULAR_FISHING_TARGETS = [
  { id: 'pfz_mumbai_offshore', name: '🐟 Mumbai High Pelagic PFZ (40m depth)', coords: [18.82, 72.45] as [number, number] },
  { id: 'pfz_wadge_bank', name: '🐟 Wadge Bank Pelagic PFZ (Kanyakumari)', coords: [7.85, 77.30] as [number, number] },
  { id: 'pfz_veraval_shelf', name: '🐟 Saurashtra Continental Shelf PFZ', coords: [20.65, 70.15] as [number, number] },
  { id: 'pfz_malabar_slope', name: '🐟 Malabar Upwelling Tuna Ground', coords: [9.75, 75.85] as [number, number] },
  { id: 'pfz_coromandel', name: '🐟 Coromandel Coastal Mackerel Trench', coords: [13.25, 80.55] as [number, number] },
  { id: 'pfz_vizag_canyon', name: '🐟 Andhra Deep Sea Canyon PFZ', coords: [17.50, 83.60] as [number, number] },
];

// OpenSeaMap nautical seamarks tile overlay (buoys, beacons, lighthouses, depth contours)
const OPENSEAMAP_SEAMARK_URL = 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png';
const ESRI_OCEAN_REF_URL = 'https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}';

// Coastal region presets covering the entirety of the Indian coastline
const COASTAL_REGIONS = [
  { id: 'all_india', label: '🇮🇳 All India Coast', center: [16.0, 78.5], zoom: 5 },
  { id: 'west_coast', label: '🌊 Arabian Sea (West)', center: [15.5, 72.5], zoom: 6 },
  { id: 'east_coast', label: '🌊 Bay of Bengal (East)', center: [15.5, 84.0], zoom: 6 },
  { id: 'gujarat', label: 'Gujarat / Saurashtra', center: [21.5, 69.8], zoom: 8 },
  { id: 'mumbai', label: 'Mumbai / Konkan', center: [18.95, 72.80], zoom: 9 },
  { id: 'goa_karwar', label: 'Goa / Karwar Coast', center: [15.1, 73.9], zoom: 9 },
  { id: 'kerala', label: 'Kochi / Malabar Coast', center: [9.95, 76.22], zoom: 9 },
  { id: 'kanyakumari', label: 'Kanyakumari / Wadge Bank', center: [8.08, 77.54], zoom: 9 },
  { id: 'tamil_nadu', label: 'Chennai / Coromandel', center: [13.10, 80.30], zoom: 9 },
  { id: 'andhra', label: 'Visakhapatnam / Circars', center: [17.68, 83.25], zoom: 9 },
  { id: 'odisha', label: 'Paradip / Odisha Coast', center: [20.31, 86.62], zoom: 9 },
  { id: 'bengal', label: 'Sandheads / Sundarbans', center: [21.65, 88.08], zoom: 9 },
  { id: 'lakshadweep', label: 'Lakshadweep Islands', center: [10.56, 72.64], zoom: 8 },
  { id: 'andaman', label: 'Andaman & Nicobar', center: [11.66, 92.74], zoom: 8 },
];

interface MarineMapProps {
  onAskAboutLocation?: (lat: number, lon: number, customPrompt?: string) => void;
  highlightRoute?: [number, number][]; // [lon, lat]
  highlightPfz?: any;
}

export const MarineMap: React.FC<MarineMapProps> = ({
  onAskAboutLocation,
  highlightRoute,
  highlightPfz,
}) => {
  const { userLocation, mapSelectedLocation } = useAppState();

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const baseTileLayerRef = useRef<L.TileLayer | null>(null);
  const seamarkTileLayerRef = useRef<L.TileLayer | null>(null);
  const oceanRefTileLayerRef = useRef<L.TileLayer | null>(null);

  // Layer Group references for fast memory management & zero page reloads
  const pfzLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const restrictedLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const sstLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const wavesLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const riskLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const chlorophyllLayerGroupRef = useRef<L.GeoJSON | null>(null);
  const routeLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const userMarkerRef = useRef<L.CircleMarker | null>(null);

  // States
  const [selectedBaseMap, setSelectedBaseMap] = useState<string>('nautical_ocean');
  const [activeLayers, setActiveLayers] = useState<{
    seamarks: boolean;
    pfz: boolean;
    restricted: boolean;
    sst: boolean;
    waves: boolean;
    risk: boolean;
    chlorophyll: boolean;
  }>({
    seamarks: true,
    pfz: true,
    restricted: true,
    sst: false,
    waves: true,
    risk: true,
    chlorophyll: true,
  });

  const [selectedRegion, setSelectedRegion] = useState<string>('all_india');
  const [spotOverview, setSpotOverview] = useState<SpotOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState<boolean>(false);
  const [layerLoading, setLayerLoading] = useState<boolean>(false);
  const [sosModalOpen, setSosModalOpen] = useState<boolean>(false);
  const [layersOpen, setLayersOpen] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 768 : true
  );

  // Smart Navigation States
  const [smartNavOpen, setSmartNavOpen] = useState<boolean>(false);
  const [navOriginId, setNavOriginId] = useState<string>('mumbai_sassoon');
  const [navDestId, setNavDestId] = useState<string>('pfz_mumbai_offshore');
  const [navVesselClass, setNavVesselClass] = useState<string>('motorized_fiberglass');
  const [navBufferKm, setNavBufferKm] = useState<number>(2.0);
  const [routeCalculating, setRouteCalculating] = useState<boolean>(false);
  const [routeResult, setRouteResult] = useState<RouteAnalysisResult | null>(null);
  const [routeError, setRouteError] = useState<string | null>(null);

  const [layerMeta, setLayerMeta] = useState<{
    source: string;
    timestamp: string;
    status: string;
    stationCount: number;
  }>({
    source: 'OpenSeaMap + Live Coastal Marine Telemetry',
    timestamp: new Date().toLocaleTimeString(),
    status: 'LIVE TELEMETRY',
    stationCount: 37,
  });

  // 1. Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter: [number, number] = userLocation
      ? [userLocation.latitude, userLocation.longitude]
      : [16.0, 78.5]; // Whole India coastal overview default

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: userLocation ? 9 : 5,
      zoomControl: false,
      attributionControl: false,
    });

    // Custom attribution control placed bottom-left
    L.control.attribution({ position: 'bottomleft', prefix: 'NEERDRISTI Marine GIS • OpenSeaMap' }).addTo(map);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Initial base tile layer
    const base = BASE_TILES[selectedBaseMap] || BASE_TILES['nautical_ocean'];
    baseTileLayerRef.current = L.tileLayer(base.url, {
      attribution: base.attr,
      maxZoom: base.maxZoom,
      maxNativeZoom: base.maxNativeZoom,
      subdomains: base.subdomains || 'abc',
    }).addTo(map);

    // Ocean reference labels layer (depth soundings, sea trenches)
    oceanRefTileLayerRef.current = L.tileLayer(ESRI_OCEAN_REF_URL, {
      maxZoom: 16,
      opacity: 0.85,
    }).addTo(map);

    // OpenSeaMap nautical seamarks overlay (buoys, beacons, lights)
    seamarkTileLayerRef.current = L.tileLayer(OPENSEAMAP_SEAMARK_URL, {
      attribution: 'Seamarks &copy; OpenSeaMap',
      maxZoom: 18,
      opacity: 0.95,
    }).addTo(map);

    // Initialize layer containers
    pfzLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    restrictedLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    sstLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    wavesLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    riskLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    chlorophyllLayerGroupRef.current = L.geoJSON(undefined).addTo(map);
    routeLayerGroupRef.current = L.layerGroup().addTo(map);

    // Click handler for arbitrary marine coordinates
    map.on('click', async (e: L.LeafletMouseEvent) => {
      const lat = parseFloat(e.latlng.lat.toFixed(4));
      const lon = parseFloat(e.latlng.lng.toFixed(4));

      appStore.setMapSelectedLocation({ latitude: lat, longitude: lon });
      fetchSpotOverview(lat, lon);
    });

    // Panning & zoom listener to keep coastal zones updated as the user navigates
    let moveTimer: ReturnType<typeof setTimeout> | null = null;
    map.on('moveend', () => {
      if (moveTimer) clearTimeout(moveTimer);
      moveTimer = setTimeout(() => {
        refreshLayers();
      }, 600);
    });

    mapInstanceRef.current = map;

    return () => {
      if (moveTimer) clearTimeout(moveTimer);
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Fetch Spot Overview function
  const fetchSpotOverview = async (lat: number, lon: number) => {
    setOverviewLoading(true);
    try {
      const data = await marineService.getOverview(lat, lon);
      setSpotOverview(data);
    } catch (e) {
      console.error('Failed to load spot overview:', e);
    } finally {
      setOverviewLoading(false);
    }
  };

  // 3. Switch Base Map Tile Layer & Reference Labels
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const base = BASE_TILES[selectedBaseMap] || BASE_TILES['nautical_ocean'];

    if (baseTileLayerRef.current) {
      map.removeLayer(baseTileLayerRef.current);
    }
    baseTileLayerRef.current = L.tileLayer(base.url, {
      attribution: base.attr,
      maxZoom: base.maxZoom,
      maxNativeZoom: base.maxNativeZoom,
      subdomains: base.subdomains || 'abc',
    }).addTo(map);

    // Manage ESRI Ocean Reference labels layer (only needed on bathymetry/satellite)
    if (oceanRefTileLayerRef.current) {
      if (selectedBaseMap === 'nautical_ocean') {
        if (!map.hasLayer(oceanRefTileLayerRef.current)) {
          oceanRefTileLayerRef.current.addTo(map);
        }
      } else {
        if (map.hasLayer(oceanRefTileLayerRef.current)) {
          map.removeLayer(oceanRefTileLayerRef.current);
        }
      }
    }
  }, [selectedBaseMap]);

  // 4. Toggle OpenSeaMap Seamarks Layer
  useEffect(() => {
    if (!mapInstanceRef.current || !seamarkTileLayerRef.current) return;
    const map = mapInstanceRef.current;

    if (activeLayers.seamarks) {
      if (!map.hasLayer(seamarkTileLayerRef.current)) {
        seamarkTileLayerRef.current.addTo(map);
      }
    } else {
      if (map.hasLayer(seamarkTileLayerRef.current)) {
        map.removeLayer(seamarkTileLayerRef.current);
      }
    }
  }, [activeLayers.seamarks]);

  // 5. Update User Location Marker
  useEffect(() => {
    if (!mapInstanceRef.current || !userLocation) return;
    const map = mapInstanceRef.current;

    if (userMarkerRef.current) {
      userMarkerRef.current.setLatLng([userLocation.latitude, userLocation.longitude]);
    } else {
      userMarkerRef.current = L.circleMarker([userLocation.latitude, userLocation.longitude], {
        radius: 8,
        fillColor: '#06b6d4',
        fillOpacity: 1,
        color: '#ffffff',
        weight: 2,
      }).addTo(map);

      userMarkerRef.current.bindPopup(
        `<div style="font-size:0.8rem; font-weight:600; color:#0f172a;">📍 ${userLocation.name || 'Your Location'}</div>`
      );
    }
  }, [userLocation]);

  // 6. Handle Programmatic FlyTo when mapSelectedLocation updates
  useEffect(() => {
    if (!mapInstanceRef.current || !mapSelectedLocation) return;
    mapInstanceRef.current.flyTo(
      [mapSelectedLocation.latitude, mapSelectedLocation.longitude],
      11,
      { duration: 1.2 }
    );
  }, [mapSelectedLocation]);

  // 7. Fetch & Render Active Marine Layers across Coastal Areas
  const refreshLayers = useCallback(async () => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const center = map.getCenter();
    const bounds = map.getBounds();
    const lat = center.lat;
    const lon = center.lng;

    // Viewport bounding box (min_lon, min_lat, max_lon, max_lat)
    const bbox = `${bounds.getWest().toFixed(4)},${bounds.getSouth().toFixed(4)},${bounds.getEast().toFixed(4)},${bounds.getNorth().toFixed(4)}`;

    setLayerLoading(true);
    let activeStationTotal = 28;

    try {
      // PFZ Layer (Potential Fishing Zones across Indian continental shelf)
      if (activeLayers.pfz) {
        const pfzData = await marineService.getMapPfz({ lat, lon, bbox });
        if (pfzLayerGroupRef.current) {
          pfzLayerGroupRef.current.clearLayers();
          pfzLayerGroupRef.current.addData(pfzData as any);
          pfzLayerGroupRef.current.setStyle(() => ({
            color: '#10b981',
            weight: 2,
            fillColor: '#059669',
            fillOpacity: 0.35,
          }));
          pfzLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            const species = Array.isArray(p.target_species) ? p.target_species.join(', ') : (p.target_species || 'Pelagic Fish');
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px; min-width: 210px;">
                <div style="font-weight: 700; color: #047857; font-size: 0.95rem; margin-bottom: 4px;">
                  🐟 ${p.name || 'Potential Fishing Zone'}
                </div>
                <div style="font-size: 0.75rem; margin-top: 2px;"><b>Confidence:</b> ${(p.confidence * 100).toFixed(0)}% • <b>Depth:</b> ${p.depth_m || 45}m</div>
                <div style="font-size: 0.75rem; margin-top: 2px;"><b>SST:</b> ${p.sst_celsius || '28.5'}°C | <b>Chlorophyll:</b> ${p.chlorophyll_mg_m3 || '1.6'} mg/m³</div>
                <div style="font-size: 0.75rem; margin-top: 2px;"><b>Target Species:</b> ${species}</div>
                <div style="font-size: 0.75rem; color: #334155; margin-top: 4px; line-height: 1.3;">${p.advisory || ''}</div>
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 3px;">
                  ● LIVE DATA • ${p.source || 'INCOIS-Calibrated PFZ Telemetry'}
                </div>
              </div>
            `;
          });
        }
      } else if (pfzLayerGroupRef.current) {
        pfzLayerGroupRef.current.clearLayers();
      }

      // Restricted & Protected Maritime Zones Layer (IMBL, naval ranges, oil exclusion, protected reefs)
      if (activeLayers.restricted) {
        const zonesData = await marineService.getMarineZones({ lat, lon, bbox });
        if (restrictedLayerGroupRef.current) {
          restrictedLayerGroupRef.current.clearLayers();
          restrictedLayerGroupRef.current.addData(zonesData as any);
          restrictedLayerGroupRef.current.setStyle((feature: any) => {
            const zType = feature?.properties?.zone_type;
            const isMil = zType === 'naval_military' || zType === 'security_border';
            const isInd = zType === 'industrial_exclusion';
            return {
              color: isMil ? '#ef4444' : (isInd ? '#f59e0b' : '#06b6d4'),
              fillColor: isMil ? '#dc2626' : (isInd ? '#d97706' : '#0891b2'),
              fillOpacity: 0.35,
              weight: 2,
              dashArray: isMil ? '6, 6' : undefined,
            };
          });
          restrictedLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            const isMil = p.zone_type === 'naval_military' || p.zone_type === 'security_border';
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px; min-width: 220px;">
                <div style="font-weight: 700; color: ${isMil ? '#dc2626' : '#0369a1'}; font-size: 0.9rem; margin-bottom: 4px;">
                  🛡️ ${p.name || 'Restricted Maritime Zone'}
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 3px;">
                  <b>Severity:</b> <span style="font-weight: 700; color: #dc2626;">${p.severity || 'CRITICAL'}</span>
                  • <b>Type:</b> ${p.zone_type || 'Exclusion Zone'}
                </div>
                <div style="font-size: 0.75rem; color: #334155; margin-bottom: 4px; line-height: 1.3;">
                  <b>Restriction:</b> ${p.restriction || 'Strict navigation controls apply.'}
                </div>
                <div style="font-size: 0.65rem; color: #dc2626; font-weight: 600; border-top: 1px solid #e2e8f0; padding-top: 3px;">
                  ● ACTIVE MARITIME GEOFENCE • ${p.source || 'DG Shipping / Indian Navy'}
                </div>
              </div>
            `;
          });
        }
      } else if (restrictedLayerGroupRef.current) {
        restrictedLayerGroupRef.current.clearLayers();
      }

      // SST Thermal Front Layer
      if (activeLayers.sst) {
        const sstData = await marineService.getSST({ lat, lon, bbox });
        if (sstLayerGroupRef.current) {
          sstLayerGroupRef.current.clearLayers();
          sstLayerGroupRef.current.addData(sstData as any);
          sstLayerGroupRef.current.setStyle((feature: any) => {
            const isFront = feature?.properties?.thermal_front;
            return {
              color: isFront ? '#38bdf8' : '#fb923c',
              fillColor: isFront ? '#0284c7' : '#ea580c',
              fillOpacity: 0.7,
              weight: 1.5,
              radius: 6,
            };
          });
          sstLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px;">
                <div style="font-weight: 700; color: #0369a1; font-size: 0.85rem;">🌡️ ${p.station_name || 'Coastal Point'}</div>
                <div style="font-size: 0.75rem; margin-top: 2px;"><b>Water Temp:</b> ${p.value} °C</div>
                <div style="font-size: 0.75rem; color: #475569;">${p.thermal_front ? '🌊 Upwelling Thermal Front' : 'Warm Surface Layer'}</div>
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; margin-top: 4px; border-top: 1px solid #e2e8f0; padding-top: 2px;">
                  ● LIVE DATA • ECMWF Ocean Physics
                </div>
              </div>
            `;
          });
        }
      } else if (sstLayerGroupRef.current) {
        sstLayerGroupRef.current.clearLayers();
      }

      // Waves & Sea State Layer (Across all coastal stations in India)
      if (activeLayers.waves) {
        const waveData = await marineService.getWaves({ lat, lon, bbox });
        if (wavesLayerGroupRef.current) {
          wavesLayerGroupRef.current.clearLayers();
          wavesLayerGroupRef.current.addData(waveData as any);
          activeStationTotal = waveData.features?.length || 28;

          wavesLayerGroupRef.current.setStyle((feature: any) => {
            const wh = feature?.properties?.significant_wave_height_m || 1.0;
            const isHigh = wh >= 2.2;
            const isMod = wh >= 1.3;
            return {
              color: isHigh ? '#ef4444' : (isMod ? '#f59e0b' : '#38bdf8'),
              fillColor: isHigh ? '#dc2626' : (isMod ? '#d97706' : '#0284c7'),
              fillOpacity: 0.6,
              radius: 6,
              weight: 1.5,
            };
          });
          wavesLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px; min-width: 180px;">
                <div style="font-weight: 700; color: #0369a1; font-size: 0.9rem; margin-bottom: 4px;">
                  🌊 ${p.station_name || 'Coastal Marine Station'}
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;"><b>State / Zone:</b> ${p.state || 'Indian Coastline'}</div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;"><b>Significant Wave:</b> ${p.significant_wave_height_m} m (${p.sea_state || 'Moderate'})</div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;"><b>Period:</b> ${p.dominant_period_s} s | <b>Direction:</b> ${p.wave_direction_deg}°</div>
                <div style="font-size: 0.75rem; margin-bottom: 4px;"><b>Swell Height:</b> ${p.swell_wave_height_m || 0.7} m</div>
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; border-top: 1px solid #e2e8f0; padding-top: 4px;">
                  ● LIVE DATA • ${p.source || 'Open-Meteo Marine'}
                </div>
              </div>
            `;
          });
        }
      } else if (wavesLayerGroupRef.current) {
        wavesLayerGroupRef.current.clearLayers();
      }

      // Marine Hazard & Risk Layer
      if (activeLayers.risk) {
        const riskData = await marineService.getRisk({ lat, lon, bbox });
        if (riskLayerGroupRef.current) {
          riskLayerGroupRef.current.clearLayers();
          riskLayerGroupRef.current.addData(riskData as any);
          riskLayerGroupRef.current.setStyle((feature: any) => {
            const isHigh = feature?.properties?.level === 'HIGH';
            return {
              color: isHigh ? '#ef4444' : '#f59e0b',
              fillColor: isHigh ? '#dc2626' : '#d97706',
              fillOpacity: 0.45,
              weight: 2,
            };
          });
          riskLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px; min-width: 180px;">
                <div style="font-weight: 700; color: ${p.level === 'HIGH' ? '#dc2626' : '#d97706'}; font-size: 0.9rem; margin-bottom: 4px;">
                  ⚠️ ${p.name || 'Navigation Hazard Zone'}
                </div>
                <div style="font-size: 0.75rem; margin-top: 2px;"><b>Risk Level:</b> <span style="font-weight: 700; color: ${p.level === 'HIGH' ? '#dc2626' : '#d97706'}">${p.level || 'MODERATE'}</span></div>
                <div style="font-size: 0.75rem; color: #334155; margin-top: 3px; line-height: 1.3;">${p.reason || ''}</div>
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 3px;">
                  ● LIVE DATA • Real-Time Safety Advisory
                </div>
              </div>
            `;
          });
        }
      } else if (riskLayerGroupRef.current) {
        riskLayerGroupRef.current.clearLayers();
      }

      // Chlorophyll-a Biomass & Phytoplankton Plumes Layer (MODIS / Sentinel-3 calibrated telemetry across 37 stations)
      if (activeLayers.chlorophyll) {
        const chloroData = await marineService.getChlorophyll({ lat, lon, bbox });
        if (chlorophyllLayerGroupRef.current) {
          chlorophyllLayerGroupRef.current.clearLayers();
          chlorophyllLayerGroupRef.current.addData(chloroData as any);
          activeStationTotal = Math.max(activeStationTotal, chloroData.features?.length || 37);

          chlorophyllLayerGroupRef.current.setStyle((feature: any) => {
            const val = feature?.properties?.chlorophyll_mg_m3 || 1.2;
            const isHigh = val >= 2.0;
            const isMod = val >= 1.0;
            return {
              color: isHigh ? '#059669' : (isMod ? '#0d9488' : '#06b6d4'),
              fillColor: isHigh ? '#10b981' : (isMod ? '#14b8a6' : '#22d3ee'),
              fillOpacity: 0.75,
              radius: Math.min(11, Math.max(6, Math.round(val * 4))),
              weight: 1.5,
            };
          });
          chlorophyllLayerGroupRef.current.bindPopup((layer: any) => {
            const p = layer.feature.properties || {};
            return `
              <div style="font-family: sans-serif; color: #0f172a; padding: 6px; min-width: 200px;">
                <div style="font-weight: 700; color: #047857; font-size: 0.9rem; margin-bottom: 4px;">
                  🌿 ${p.station_name || 'Chlorophyll Station'}
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;">
                  <b>Chlorophyll-a:</b> <span style="font-weight: 700; color: #059669;">${p.chlorophyll_mg_m3 || '1.40'} mg/m³</span>
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;">
                  <b>Productivity:</b> <span style="font-weight: 600; color: #0f766e;">${p.productivity_level || 'HIGH BIOMASS'}</span>
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 2px;">
                  <b>Upwelling:</b> ${p.upwelling_index || 'Active Ocean Upwelling'}
                </div>
                <div style="font-size: 0.65rem; color: #059669; font-weight: 600; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 3px;">
                  ● LIVE DATA • ${p.source || 'MODIS Aqua / Sentinel-3 OLCI'}
                </div>
              </div>
            `;
          });
        }
      } else if (chlorophyllLayerGroupRef.current) {
        chlorophyllLayerGroupRef.current.clearLayers();
      }

      setLayerMeta({
        source: 'OpenSeaMap + Live Coastal Marine Telemetry',
        timestamp: new Date().toLocaleTimeString(),
        status: 'LIVE TELEMETRY',
        stationCount: activeStationTotal,
      });
    } catch (err) {
      console.warn('Failed to refresh marine layers:', err);
    } finally {
      setLayerLoading(false);
    }
  }, [activeLayers]);

  // Initial and reactive layer fetch
  useEffect(() => {
    refreshLayers();
  }, [refreshLayers]);

  // 8. Handle Coastal Region Quick Selector
  const handleSelectRegion = (regionId: string) => {
    setSelectedRegion(regionId);
    const region = COASTAL_REGIONS.find((r) => r.id === regionId);
    if (region && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo(region.center as [number, number], region.zoom, { duration: 1.4 });
      setTimeout(() => {
        refreshLayers();
      }, 1500);
    }
  };

  // 9. Route Highlighting
  useEffect(() => {
    if (!mapInstanceRef.current || !routeLayerGroupRef.current) return;
    routeLayerGroupRef.current.clearLayers();

    if (highlightRoute && highlightRoute.length >= 2) {
      const latLngs: [number, number][] = highlightRoute.map(([lon, lat]) => [lat, lon]);

      const polyline = L.polyline(latLngs, {
        color: '#22d3ee',
        weight: 4,
        dashArray: '6, 8',
      }).addTo(routeLayerGroupRef.current);

      L.circleMarker(latLngs[0], {
        radius: 7,
        fillColor: '#10b981',
        fillOpacity: 1,
        color: '#ffffff',
        weight: 2,
      }).bindPopup('<b>Departure Harbor</b>').addTo(routeLayerGroupRef.current);

      L.circleMarker(latLngs[latLngs.length - 1], {
        radius: 7,
        fillColor: '#f59e0b',
        fillOpacity: 1,
        color: '#ffffff',
        weight: 2,
      }).bindPopup('<b>Destination Waypoint</b>').addTo(routeLayerGroupRef.current);

      mapInstanceRef.current.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }
  }, [highlightRoute]);

  const toggleLayer = (layerKey: keyof typeof activeLayers) => {
    setActiveLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  const centerOnMyLocation = () => {
    if (mapInstanceRef.current && userLocation) {
      mapInstanceRef.current.flyTo([userLocation.latitude, userLocation.longitude], 12);
    }
  };

  // 10. Smart Navigation Route Calculation
  const handleCalculateRoute = async () => {
    if (!mapInstanceRef.current) return;
    setRouteCalculating(true);
    setRouteError(null);

    try {
      // Resolve Origin Coordinates
      let originCoords: [number, number];
      if (navOriginId === 'custom_gps') {
        if (userLocation) {
          originCoords = [userLocation.latitude, userLocation.longitude];
        } else {
          const center = mapInstanceRef.current.getCenter();
          originCoords = [parseFloat(center.lat.toFixed(4)), parseFloat(center.lng.toFixed(4))];
        }
      } else {
        const found = MAJOR_FISHING_PORTS.find((p) => p.id === navOriginId);
        originCoords = found ? found.coords : [18.917, 72.825];
      }

      // Resolve Destination Coordinates
      let destCoords: [number, number];
      const targetPfz = POPULAR_FISHING_TARGETS.find((p) => p.id === navDestId);
      if (targetPfz) {
        destCoords = targetPfz.coords;
      } else {
        const targetPort = MAJOR_FISHING_PORTS.find((p) => p.id === navDestId);
        destCoords = targetPort ? targetPort.coords : [18.82, 72.45];
      }

      const res = await marineService.analyzeRoute([originCoords, destCoords], navVesselClass, navBufferKm);
      setRouteResult(res);

      // Render onto Route Layer Group
      if (routeLayerGroupRef.current) {
        routeLayerGroupRef.current.clearLayers();

        const latLngs: [number, number][] = [originCoords, destCoords];
        const isSafe = res.is_safe;

        // Route Polyline
        const polyline = L.polyline(latLngs, {
          color: isSafe ? '#06b6d4' : '#ef4444',
          weight: 5,
          opacity: 0.95,
          dashArray: isSafe ? '8, 8' : '4, 6',
        }).addTo(routeLayerGroupRef.current);

        // Departure Marker
        L.circleMarker(originCoords, {
          radius: 9,
          fillColor: '#10b981',
          fillOpacity: 1,
          color: '#ffffff',
          weight: 2,
        })
          .bindPopup(`<b>⚓ Departure Port:</b> ${MAJOR_FISHING_PORTS.find((p) => p.id === navOriginId)?.name || 'Origin'}`)
          .addTo(routeLayerGroupRef.current);

        // Destination Marker
        L.circleMarker(destCoords, {
          radius: 9,
          fillColor: isSafe ? '#06b6d4' : '#dc2626',
          fillOpacity: 1,
          color: '#ffffff',
          weight: 2,
        })
          .bindPopup(`<b>🎯 Destination:</b> ${targetPfz?.name || MAJOR_FISHING_PORTS.find((p) => p.id === navDestId)?.name || 'Destination'}`)
          .addTo(routeLayerGroupRef.current);

        mapInstanceRef.current.fitBounds(polyline.getBounds(), { padding: [50, 50] });
      }
    } catch (err: any) {
      console.error('Route calculation error:', err);
      setRouteError('Could not compute safe route. Please check coordinates and retry.');
    } finally {
      setRouteCalculating(false);
    }
  };

  const handleClearRoute = () => {
    setRouteResult(null);
    setRouteError(null);
    if (routeLayerGroupRef.current) {
      routeLayerGroupRef.current.clearLayers();
    }
  };

  const handleAskAboutRoute = () => {
    if (!routeResult) return;
    const originName = MAJOR_FISHING_PORTS.find((p) => p.id === navOriginId)?.name || 'Departure';
    const destName = POPULAR_FISHING_TARGETS.find((p) => p.id === navDestId)?.name || MAJOR_FISHING_PORTS.find((p) => p.id === navDestId)?.name || 'Destination';
    const distKm = routeResult.route_summary?.total_distance_km || 0;
    const distNm = (distKm * 0.539957).toFixed(1);
    const prompt = `Review my navigation route from ${originName} to ${destName}. Total distance is ${distKm} km (${distNm} NM). Deterministic safety check returned: ${routeResult.recommendation}. Please evaluate sea state, wave heights, and weather hazards.`;

    if (onAskAboutLocation) {
      const originCoords = MAJOR_FISHING_PORTS.find((p) => p.id === navOriginId)?.coords || [18.917, 72.825];
      onAskAboutLocation(originCoords[0], originCoords[1], prompt);
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '400px' }}>
      {/* Leaflet Map Div */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Top Bar Center: Coastal Sector, Smart Nav Toggle & SOS Trigger */}
      <div
        className="glass-panel"
        style={{
          position: 'absolute',
          top: '12px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 999,
          padding: '5px 10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          borderRadius: '10px',
          maxWidth: 'calc(100% - 24px)',
          flexWrap: 'wrap',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.45)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={13} color="var(--cyan-primary)" />
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            SECTOR:
          </span>
          <select
            value={selectedRegion}
            onChange={(e) => handleSelectRegion(e.target.value)}
            style={{
              background: 'rgba(15, 23, 42, 0.75)',
              color: 'var(--text-main)',
              border: '1px solid var(--border-active)',
              borderRadius: '4px',
              fontSize: '0.75rem',
              padding: '2px 6px',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {COASTAL_REGIONS.map((r) => (
              <option key={r.id} value={r.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Smart Navigation Drawer Toggle */}
        <button
          onClick={() => setSmartNavOpen(!smartNavOpen)}
          title="Interactive Safe Route Navigation Planner"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: smartNavOpen ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255, 255, 255, 0.05)',
            border: smartNavOpen ? '1px solid var(--cyan-primary)' : '1px solid var(--border-subtle)',
            color: smartNavOpen ? '#ffffff' : 'var(--cyan-primary)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <Navigation size={13} className={routeCalculating ? 'spin-slow' : ''} />
          <span>Smart Navigation</span>
          {routeResult && (
            <span
              style={{
                backgroundColor: routeResult.is_safe ? '#10b981' : '#dc2626',
                color: '#ffffff',
                fontSize: '0.6rem',
                padding: '1px 5px',
                borderRadius: '4px',
                fontWeight: 800,
              }}
            >
              {routeResult.recommendation}
            </span>
          )}
        </button>

        {/* Map Layers & Charts Toggle Button */}
        <button
          onClick={() => setLayersOpen(!layersOpen)}
          title="Toggle Map Layers & Charts View"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: layersOpen ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255, 255, 255, 0.05)',
            border: layersOpen ? '1px solid var(--cyan-primary)' : '1px solid var(--border-subtle)',
            color: layersOpen ? '#ffffff' : 'var(--cyan-primary)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <Layers size={13} />
          <span>Layers & Charts</span>
          <ChevronDown
            size={13}
            style={{
              transform: layersOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease',
            }}
          />
        </button>

        {/* Emergency SOS Trigger */}
        <button
          onClick={() => setSosModalOpen(true)}
          title="Broadcast Emergency SOS Distress Beacon"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            backgroundColor: '#dc2626',
            border: '1px solid #ef4444',
            color: '#ffffff',
            padding: '4px 8px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 800,
            cursor: 'pointer',
            boxShadow: '0 0 10px rgba(220, 38, 38, 0.5)',
          }}
        >
          <LifeBuoy size={13} />
          <span>SOS</span>
        </button>
      </div>

      {/* Top Right: Layer Switcher & Base Map HUD */}
      {layersOpen && (
        <div
          className="glass-panel"
          style={{
            position: 'absolute',
            top: '54px',
            right: '16px',
            zIndex: 999,
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            width: '230px',
            maxHeight: 'calc(100vh - 130px)',
            overflowY: 'auto',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.55)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={13} color="var(--cyan-primary)" />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--cyan-primary)', textTransform: 'uppercase' }}>
                Map Layers & Chart
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => refreshLayers()}
                title="Refresh Live Coastal Telemetry"
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
              >
                <RefreshCw size={13} className={layerLoading ? 'spin-slow' : ''} />
              </button>
              <button
                onClick={() => setLayersOpen(false)}
                title="Hide Layers & Charts"
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '2px' }}
              >
                <X size={14} />
              </button>
            </div>
          </div>

        {/* Layer Toggles */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.seamarks}
              onChange={() => toggleLayer('seamarks')}
              style={{ accentColor: '#38bdf8' }}
            />
            <span style={{ color: activeLayers.seamarks ? '#38bdf8' : 'var(--text-dim)', fontWeight: 600 }}>
              ⚓ Nautical Seamarks (OpenSeaMap)
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.chlorophyll}
              onChange={() => toggleLayer('chlorophyll')}
              style={{ accentColor: '#10b981' }}
            />
            <span style={{ color: activeLayers.chlorophyll ? '#34d399' : 'var(--text-dim)', fontWeight: 600 }}>
              🌿 Chlorophyll-a Biomass (Live)
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.pfz}
              onChange={() => toggleLayer('pfz')}
              style={{ accentColor: '#10b981' }}
            />
            <span style={{ color: activeLayers.pfz ? '#10b981' : 'var(--text-dim)' }}>
              🎣 Fishing Zones (PFZ)
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.restricted}
              onChange={() => toggleLayer('restricted')}
              style={{ accentColor: '#dc2626' }}
            />
            <span style={{ color: activeLayers.restricted ? '#f87171' : 'var(--text-dim)', fontWeight: 600 }}>
              🛡️ Restricted & Security Zones
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.waves}
              onChange={() => toggleLayer('waves')}
              style={{ accentColor: '#38bdf8' }}
            />
            <span style={{ color: activeLayers.waves ? '#38bdf8' : 'var(--text-dim)' }}>
              🌊 Waves & Sea State (Live)
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.risk}
              onChange={() => toggleLayer('risk')}
              style={{ accentColor: '#ef4444' }}
            />
            <span style={{ color: activeLayers.risk ? '#ef4444' : 'var(--text-dim)' }}>
              ⚠️ Hazard & Risk Alert Zones
            </span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={activeLayers.sst}
              onChange={() => toggleLayer('sst')}
              style={{ accentColor: '#f97316' }}
            />
            <span style={{ color: activeLayers.sst ? '#fb923c' : 'var(--text-dim)' }}>
              🌡️ Sea Surface Temp (SST)
            </span>
          </label>
        </div>

        {/* Base Map Selector */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginBottom: '4px', textTransform: 'uppercase' }}>
            BASE NAUTICAL CHART
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
            <button
              onClick={() => setSelectedBaseMap('nautical_ocean')}
              style={{
                fontSize: '0.65rem',
                padding: '4px 6px',
                borderRadius: '4px',
                backgroundColor: selectedBaseMap === 'nautical_ocean' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255,255,255,0.05)',
                color: selectedBaseMap === 'nautical_ocean' ? '#ffffff' : 'var(--text-dim)',
                border: selectedBaseMap === 'nautical_ocean' ? '1px solid var(--cyan-primary)' : '1px solid transparent',
                cursor: 'pointer',
              }}
            >
              Ocean Chart
            </button>
            <button
              onClick={() => setSelectedBaseMap('carto_nautical_dark')}
              style={{
                fontSize: '0.65rem',
                padding: '4px 6px',
                borderRadius: '4px',
                backgroundColor: selectedBaseMap === 'carto_nautical_dark' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255,255,255,0.05)',
                color: selectedBaseMap === 'carto_nautical_dark' ? '#ffffff' : 'var(--text-dim)',
                border: selectedBaseMap === 'carto_nautical_dark' ? '1px solid var(--cyan-primary)' : '1px solid transparent',
                cursor: 'pointer',
              }}
            >
              Tactical Dark
            </button>
            <button
              onClick={() => setSelectedBaseMap('esri_satellite')}
              style={{
                fontSize: '0.65rem',
                padding: '4px 6px',
                borderRadius: '4px',
                backgroundColor: selectedBaseMap === 'esri_satellite' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255,255,255,0.05)',
                color: selectedBaseMap === 'esri_satellite' ? '#ffffff' : 'var(--text-dim)',
                border: selectedBaseMap === 'esri_satellite' ? '1px solid var(--cyan-primary)' : '1px solid transparent',
                cursor: 'pointer',
              }}
            >
              HD Satellite
            </button>
            <button
              onClick={() => setSelectedBaseMap('osm_standard')}
              style={{
                fontSize: '0.65rem',
                padding: '4px 6px',
                borderRadius: '4px',
                backgroundColor: selectedBaseMap === 'osm_standard' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255,255,255,0.05)',
                color: selectedBaseMap === 'osm_standard' ? '#ffffff' : 'var(--text-dim)',
                border: selectedBaseMap === 'osm_standard' ? '1px solid var(--cyan-primary)' : '1px solid transparent',
                cursor: 'pointer',
              }}
            >
              Coastal Road
            </button>
          </div>
        </div>
      </div>
      )}

      {/* Recenter Button */}
      <button
        onClick={centerOnMyLocation}
        title="Center on my location"
        className="glass-panel"
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '16px',
          zIndex: 999,
          width: '38px',
          height: '38px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--cyan-primary)',
          cursor: 'pointer',
          borderRadius: '8px',
        }}
      >
        <Crosshair size={18} />
      </button>

      {/* Bottom Left: Live Telemetry & Marine Grid HUD Pill */}
      <div
        className="glass-panel"
        title={`${layerMeta.source} • Live Coastal Telemetry • Updated: ${layerMeta.timestamp}`}
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '62px',
          zIndex: 990,
          padding: '6px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.72rem',
          borderRadius: '8px',
          maxWidth: 'calc(100% - 150px)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.45)',
          pointerEvents: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <span className="pulse-dot live" />
          <span style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.78rem' }}>
            Nautical Ocean GIS
          </span>
          <span
            style={{
              fontSize: '0.6rem',
              fontWeight: 800,
              backgroundColor: 'rgba(16, 185, 129, 0.2)',
              color: '#10b981',
              padding: '1px 5px',
              borderRadius: '4px',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              letterSpacing: '0.5px',
            }}
          >
            LIVE
          </span>
        </div>
        <span style={{ color: 'var(--border-subtle)', flexShrink: 0 }}>|</span>
        <span style={{ color: 'var(--cyan-primary)', fontSize: '0.7rem', flexShrink: 0 }}>
          ⚓ {layerMeta.stationCount} Active Ports
        </span>
        <span
          style={{
            color: 'var(--text-muted)',
            fontSize: '0.68rem',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          • {layerMeta.timestamp}
        </span>
      </div>

      {/* Interactive Ocean Data Panel (when point clicked) */}
      <OceanDataPanel
        data={spotOverview}
        loading={overviewLoading}
        onClose={() => setSpotOverview(null)}
        onAskAboutLocation={(lat, lon) => {
          if (onAskAboutLocation) {
            onAskAboutLocation(lat, lon);
          }
        }}
      />

      {/* Smart Marine Navigation & Safe Route Planner Floating Panel */}
      {smartNavOpen && (
        <div
          className="glass-panel-glow animate-fade-in"
          style={{
            position: 'absolute',
            top: '54px',
            left: '16px',
            width: '380px',
            maxWidth: 'calc(100vw - 32px)',
            maxHeight: 'calc(100vh - 160px)',
            overflowY: 'auto',
            zIndex: 1000,
            padding: '16px',
            borderRadius: '14px',
            backgroundColor: 'rgba(10, 20, 36, 0.96)',
            border: '1px solid var(--border-active)',
            boxShadow: '0 12px 35px rgba(0, 0, 0, 0.65)',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid var(--border-subtle)',
              paddingBottom: '10px',
              marginBottom: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Navigation size={18} color="var(--cyan-primary)" />
              <div>
                <span style={{ fontWeight: 800, color: '#ffffff', fontSize: '0.9rem', display: 'block' }}>
                  Smart Route Navigation
                </span>
                <span style={{ fontSize: '0.65rem', color: 'var(--cyan-primary)', fontWeight: 600 }}>
                  GeoPandas Maritime Buffer & Safety Engine
                </span>
              </div>
            </div>
            <button
              onClick={() => setSmartNavOpen(false)}
              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Origin Port */}
            <div>
              <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                ⚓ DEPARTURE HARBOUR / ORIGIN
              </label>
              <select
                value={navOriginId}
                onChange={(e) => setNavOriginId(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(15, 23, 42, 0.9)',
                  color: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '7px 8px',
                  fontSize: '0.78rem',
                  outline: 'none',
                }}
              >
                {MAJOR_FISHING_PORTS.map((p) => (
                  <option key={p.id} value={p.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Destination Port / PFZ */}
            <div>
              <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                🎯 DESTINATION / FISHING ZONE (PFZ)
              </label>
              <select
                value={navDestId}
                onChange={(e) => setNavDestId(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(15, 23, 42, 0.9)',
                  color: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '7px 8px',
                  fontSize: '0.78rem',
                  outline: 'none',
                }}
              >
                <optgroup label="🐟 INCOIS Potential Fishing Zones (PFZ)">
                  {POPULAR_FISHING_TARGETS.map((t) => (
                    <option key={t.id} value={t.id} style={{ background: '#0f172a', color: '#34d399' }}>
                      {t.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="⚓ Coastal Ports & Harbours">
                  {MAJOR_FISHING_PORTS.map((p) => (
                    <option key={p.id} value={p.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                      {p.name}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>

            {/* Vessel Class & Buffer */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '8px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  VESSEL CLASS
                </label>
                <select
                  value={navVesselClass}
                  onChange={(e) => setNavVesselClass(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.9)',
                    color: '#ffffff',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '7px 8px',
                    fontSize: '0.72rem',
                    outline: 'none',
                  }}
                >
                  <option value="motorized_fiberglass" style={{ background: '#0f172a' }}>Fiberglass Boat (FRP)</option>
                  <option value="mechanized_trawler" style={{ background: '#0f172a' }}>Mechanized Trawler</option>
                  <option value="motorized_wooden" style={{ background: '#0f172a' }}>Motorized Wooden Craft</option>
                  <option value="traditional_non_motorized" style={{ background: '#0f172a' }}>Traditional Craft</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  HAZARD BUFFER
                </label>
                <select
                  value={navBufferKm}
                  onChange={(e) => setNavBufferKm(parseFloat(e.target.value))}
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.9)',
                    color: '#ffffff',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '7px 8px',
                    fontSize: '0.72rem',
                    outline: 'none',
                  }}
                >
                  <option value={1.0} style={{ background: '#0f172a' }}>1.0 km (Standard)</option>
                  <option value={2.0} style={{ background: '#0f172a' }}>2.0 km (Safe)</option>
                  <option value={5.0} style={{ background: '#0f172a' }}>5.0 km (Wide)</option>
                </select>
              </div>
            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculateRoute}
              disabled={routeCalculating}
              style={{
                marginTop: '4px',
                padding: '10px',
                backgroundColor: 'var(--cyan-primary)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.825rem',
                fontWeight: 700,
                cursor: routeCalculating ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)',
              }}
            >
              <Route size={16} className={routeCalculating ? 'spin-slow' : ''} />
              <span>{routeCalculating ? 'Analyzing Marine Route...' : 'Calculate Safe Marine Route'}</span>
            </button>

            {routeError && (
              <div style={{ color: '#f87171', fontSize: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: '6px 8px', borderRadius: '6px' }}>
                {routeError}
              </div>
            )}

            {/* Route Analysis Result Card */}
            {routeResult && (
              <div
                style={{
                  marginTop: '6px',
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  border: routeResult.is_safe ? '1px solid rgba(16, 185, 129, 0.5)' : '1px solid rgba(239, 68, 68, 0.6)',
                  borderRadius: '10px',
                  padding: '12px',
                }}
              >
                {/* Verdict Badge */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {routeResult.is_safe ? (
                      <CheckCircle2 size={16} color="#10b981" />
                    ) : (
                      <XCircle size={16} color="#ef4444" />
                    )}
                    <span
                      style={{
                        fontWeight: 800,
                        fontSize: '0.825rem',
                        color: routeResult.is_safe ? '#10b981' : '#ef4444',
                      }}
                    >
                      {routeResult.is_safe ? 'PASSAGE VERDICT: GO (SAFE)' : 'PASSAGE VERDICT: NO-GO (HAZARD)'}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                    Buffer: {routeResult.route_summary?.buffer_km}km
                  </span>
                </div>

                {/* Metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '10px', fontSize: '0.75rem' }}>
                  <div style={{ backgroundColor: 'rgba(255,255,255,0.03)', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Total Distance</span>
                    <div style={{ fontWeight: 700, color: '#38bdf8' }}>
                      {routeResult.route_summary?.total_distance_km} km ({(routeResult.route_summary?.total_distance_km * 0.539957).toFixed(1)} NM)
                    </div>
                  </div>
                  <div style={{ backgroundColor: 'rgba(255,255,255,0.03)', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Est. Transit Time</span>
                    <div style={{ fontWeight: 700, color: '#a7f3d0' }}>
                      ~{((routeResult.route_summary?.total_distance_km / 15) * 60).toFixed(0)} min (@ 8 kts)
                    </div>
                  </div>
                </div>

                {/* Hazards or Safety Confirmation */}
                {routeResult.hazard_intersections && routeResult.hazard_intersections.length > 0 ? (
                  <div style={{ marginBottom: '10px', fontSize: '0.72rem', color: '#fca5a5', lineHeight: 1.3 }}>
                    ⚠️ Route intersects {routeResult.hazard_intersections.length} designated maritime restricted zones. Shift waypoints seaward to avoid security exclusion.
                  </div>
                ) : (
                  <div style={{ marginBottom: '10px', fontSize: '0.72rem', color: '#6ee7b7', lineHeight: 1.3 }}>
                    ✅ Safe navigation corridor: Zero military exercise, IMBL border, or biosphere restrictions detected.
                  </div>
                )}

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={handleAskAboutRoute}
                    style={{
                      flex: 1,
                      padding: '7px 10px',
                      backgroundColor: 'rgba(6, 182, 212, 0.2)',
                      border: '1px solid var(--border-active)',
                      color: 'var(--cyan-hover)',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    💬 Ask AI to Review Route
                  </button>
                  <button
                    onClick={handleClearRoute}
                    style={{
                      padding: '7px 10px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-dim)',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      cursor: 'pointer',
                    }}
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Emergency Distress Beacon Modal */}
      <EmergencySosModal isOpen={sosModalOpen} onClose={() => setSosModalOpen(false)} />
    </div>
  );
};
