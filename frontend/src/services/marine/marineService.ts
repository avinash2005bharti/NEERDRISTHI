import { apiRequest } from '../api/client';
import {
  MarineMapConfig,
  GeoJsonFeatureCollection,
  SpotOverview,
  RouteAnalysisResult,
} from '../../types';

export interface ViewportParams {
  lat?: number;
  lon?: number;
  bbox?: string;
  zoom?: number;
}

function buildQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return '';
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') {
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
    }
  }
  return parts.length > 0 ? `?${parts.join('&')}` : '';
}

export const marineService = {
  /**
   * Fetch map configuration & base layers
   */
  async getMapConfig(): Promise<MarineMapConfig> {
    const res = await apiRequest<{ success: boolean; data: MarineMapConfig }>('/marine/map/config');
    return res.data;
  },

  /**
   * Fetch Sea Surface Temperature (SST) layer (GeoJSON)
   */
  async getSST(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/sst${buildQuery(params as any)}`);
  },

  /**
   * Fetch Chlorophyll-a layer (GeoJSON)
   */
  async getChlorophyll(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/chlorophyll${buildQuery(params as any)}`);
  },

  /**
   * Fetch Waves & Swell layer (GeoJSON)
   */
  async getWaves(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/waves${buildQuery(params as any)}`);
  },

  /**
   * Fetch Wind Vectors & Gusts layer (GeoJSON)
   */
  async getWind(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/wind${buildQuery(params as any)}`);
  },

  /**
   * Fetch Tidal water level predictions (GeoJSON/point)
   */
  async getTides(lat: number, lon: number): Promise<Record<string, unknown>> {
    return apiRequest<Record<string, unknown>>(`/marine/tides?lat=${lat}&lon=${lon}`);
  },

  /**
   * Fetch Marine Risk & hazard zones (GeoJSON)
   */
  async getRisk(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/risk${buildQuery(params as any)}`);
  },

  /**
   * Fetch Potential Fishing Zones (PFZ) GeoJSON layer
   */
  async getMapPfz(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/map/pfz${buildQuery(params as any)}`);
  },

  /**
   * Fetch Restricted & Security Maritime Zones GeoJSON layer (IMBL, naval ranges, biospheres)
   */
  async getMarineZones(params?: ViewportParams): Promise<GeoJsonFeatureCollection> {
    return apiRequest<GeoJsonFeatureCollection>(`/marine/map/zones${buildQuery(params as any)}`);
  },

  /**
   * Unified Marine overview snapshot at clicked/selected point
   */
  async getOverview(lat: number, lon: number): Promise<SpotOverview> {
    return apiRequest<SpotOverview>(`/marine/overview?lat=${lat}&lon=${lon}`);
  },

  /**
   * Point weather telemetry
   */
  async getWeather(lat: number, lon: number): Promise<Record<string, unknown>> {
    const res = await apiRequest<{ success: boolean; data: Record<string, unknown> }>(
      `/marine/weather?latitude=${lat}&longitude=${lon}`
    );
    return res.data;
  },

  /**
   * Satellite observations at location
   */
  async getSatellite(lat: number, lon: number): Promise<Record<string, unknown>> {
    const res = await apiRequest<{ success: boolean; data: Record<string, unknown> }>(
      `/marine/satellite?latitude=${lat}&longitude=${lon}`
    );
    return res.data;
  },

  /**
   * Experimental PFZ suitability calculation
   */
  async getFishingZoneEstimate(lat: number, lon: number): Promise<Record<string, unknown>> {
    const res = await apiRequest<{ success: boolean; data: Record<string, unknown> }>(
      `/marine/fishing-zone?latitude=${lat}&longitude=${lon}`
    );
    return res.data;
  },

  /**
   * Deterministic route safety analysis
   */
  async analyzeRoute(
    waypoints: [number, number][],
    vesselClass?: string,
    bufferKm?: number
  ): Promise<RouteAnalysisResult> {
    const res = await apiRequest<{ success: boolean; data: RouteAnalysisResult }>(
      '/marine/route-analysis',
      {
        method: 'POST',
        body: JSON.stringify({
          waypoints,
          vesselClass: vesselClass || 'motorized_fiberglass',
          bufferKm: bufferKm || 2.0,
        }),
      }
    );
    return res.data;
  },

  /**
   * Deterministic risk analysis
   */
  async analyzeRisk(
    latitude: number,
    longitude: number,
    vesselClass?: string
  ): Promise<Record<string, unknown>> {
    const res = await apiRequest<{ success: boolean; data: Record<string, unknown> }>(
      '/marine/risk-analysis',
      {
        method: 'POST',
        body: JSON.stringify({
          latitude,
          longitude,
          vesselClass: vesselClass || 'motorized_fiberglass',
        }),
      }
    );
    return res.data;
  },
};
