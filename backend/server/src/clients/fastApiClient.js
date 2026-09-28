import axios from 'axios';
import { env } from '../config/env.js';
import { logger } from '../utils/logger.js';
import { UpstreamServiceError } from '../utils/errors.js';

export class FastApiClient {
  constructor() {
    this.client = axios.create({
      baseURL: env.FASTAPI_INTERNAL_URL,
      timeout: 60000, // 60s max for multi-agent reasoning
      headers: {
        'Content-Type': 'application/json',
        'x-internal-service-secret': env.INTERNAL_SERVICE_SECRET || '',
      },
    });
  }

  async checkHealth() {
    try {
      const response = await this.client.get('/health', { timeout: 3000 });
      return { status: 'healthy', details: response.data };
    } catch (error) {
      logger.warn({ error: error.message }, 'FastAPI health check failed');
      return {
        status: 'unreachable',
        details: error.response?.data || error.message,
      };
    }
  }

  async executeWorkflow(request, requestId) {
    try {
      logger.info({ requestId }, 'Dispatching workflow execution to FastAPI agent core');
      const url = '/internal/ai/chat';
      const response = await this.client.post(url, request, {
        headers: {
          'x-request-id': requestId,
        },
      });
      return response.data;
    } catch (error) {
      logger.error(
        {
          requestId,
          err: error.message,
          status: error.response?.status,
          data: error.response?.data,
        },
        'FastAPI workflow execution failed'
      );

      if (error.response?.data?.detail) {
        throw new UpstreamServiceError(
          `Agent Core error: ${JSON.stringify(error.response.data.detail)}`
        );
      }
      throw new UpstreamServiceError(
        'The marine agent reasoning core is currently unreachable or timed out.',
        { originalError: error.message }
      );
    }
  }

  async executeMarineAnalysis(request, requestId) {
    try {
      const response = await this.client.post('/internal/ai/analyze', request, {
        headers: { 'x-request-id': requestId },
      });
      return response.data;
    } catch (error) {
      throw new UpstreamServiceError('Failed to execute marine analysis in agent core');
    }
  }

  async executeRouteAnalysis(waypoints, vesselClass, bufferKm) {
    try {
      const response = await this.client.post('/internal/ai/route-analysis', {
        waypoints,
        vessel_class: vesselClass || 'motorized_fiberglass',
        buffer_km: bufferKm || 2.0,
      });
      return response.data;
    } catch (error) {
      logger.error({ err: error.message }, 'Failed route analysis in FastAPI');
      throw new UpstreamServiceError('Failed to execute GIS route analysis');
    }
  }

  async executeRiskAnalysis(vesselClass, latitude, longitude) {
    try {
      const response = await this.client.post('/internal/ai/risk-analysis', {
        vessel_class: vesselClass,
        latitude,
        longitude,
      });
      return response.data;
    } catch (error) {
      throw new UpstreamServiceError('Failed to evaluate deterministic risk');
    }
  }

  async executeSandbox(code, datasetCsv, contextData, timeoutSeconds) {
    try {
      const response = await this.client.post('/internal/ai/sandbox/execute', {
        code,
        dataset_csv: datasetCsv || null,
        context_data: contextData || {},
        timeout_seconds: timeoutSeconds || 10.0,
      });
      return response.data;
    } catch (error) {
      logger.error({ err: error.message }, 'Sandbox execution request failed');
      throw new UpstreamServiceError('Isolated sandbox execution failed');
    }
  }

  async getRequestStatus(requestId) {
    try {
      const response = await this.client.get(
        `/internal/v1/orca/request/${encodeURIComponent(requestId)}`
      );
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        return null;
      }
      throw new UpstreamServiceError('Failed to fetch request status from agent core');
    }
  }

  // ─── Direct Marine Scientific Telemetry Endpoints ─────────────────────────

  async getMarineWeather(latitude, longitude) {
    try {
      const response = await this.client.get('/internal/ai/marine/weather', {
        params: { latitude, longitude },
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine weather from FastAPI');
      return { status: 'unavailable', reason: 'Weather service temporarily unreachable' };
    }
  }

  async getOceanState(latitude, longitude) {
    try {
      const response = await this.client.get('/internal/ai/marine/ocean', {
        params: { latitude, longitude },
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch ocean state from FastAPI');
      return { status: 'unavailable', reason: 'Ocean state service temporarily unreachable' };
    }
  }

  async getPFZData(latitude, longitude) {
    try {
      const response = await this.client.get('/internal/ai/marine/pfz', {
        params: { latitude, longitude },
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch PFZ data from FastAPI');
      return { status: 'unavailable', reason: 'PFZ data service temporarily unreachable' };
    }
  }

  async getMarineAlerts(latitude, longitude) {
    try {
      const params = {};
      if (latitude !== undefined) params.latitude = latitude;
      if (longitude !== undefined) params.longitude = longitude;
      const response = await this.client.get('/internal/ai/marine/alerts', {
        params,
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine alerts from FastAPI');
      return { status: 'unavailable', alerts: [], reason: 'Alert service temporarily unreachable' };
    }
  }

  async getMarineZones(latitude, longitude, radiusKm) {
    try {
      const params = {};
      if (latitude !== undefined) params.latitude = latitude;
      if (longitude !== undefined) params.longitude = longitude;
      if (radiusKm !== undefined) params.radius_km = radiusKm;
      const response = await this.client.get('/internal/ai/marine/zones', {
        params,
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine zones from FastAPI');
      return {
        type: 'FeatureCollection',
        features: [],
        status: 'unavailable',
        reason: 'Marine zones service temporarily unreachable',
      };
    }
  }

  async getMarineMapConfig() {
    try {
      const response = await this.client.get('/api/marine/map/config', { timeout: 10000 });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine map config from FastAPI');
      return { status: 'fallback', demo_mode: true, base_maps: [], marine_layers: [] };
    }
  }

  async getMarineLayer(layerName, params = {}) {
    try {
      const response = await this.client.get(`/api/marine/${layerName}`, {
        params,
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message, layer: layerName }, 'Failed to fetch marine layer from FastAPI');
      return { type: 'FeatureCollection', features: [], status: 'unavailable', is_live: false };
    }
  }

  async getSatelliteObservations(latitude, longitude) {
    try {
      const response = await this.client.get('/satellite/observations', {
        params: { latitude, longitude },
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch satellite observations from FastAPI');
      return { status: 'unavailable', records: [], reason: 'Satellite service temporarily unreachable' };
    }
  }

  async getFishingZoneEstimate(latitude, longitude) {
    try {
      const response = await this.client.get('/fishing-zone/estimate', {
        params: { latitude, longitude },
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch fishing-zone estimate from FastAPI');
      return { status: 'unavailable', data: null, reason: 'Fishing-zone estimate temporarily unreachable' };
    }
  }
}

export const fastApiClient = new FastApiClient();
