import axios from 'axios';
import { env } from '../config/env.js';
import { logger } from '../utils/logger.js';
import { UpstreamServiceError, AiServiceUnavailableError } from '../utils/errors.js';

export class FastApiClient {
  constructor() {
    // Configurable timeouts suitable for Render cold-starts and AI multi-agent reasoning
    this.workflowTimeoutMs = 90000;   // 90s for multi-agent reasoning (LangGraph + LLM synthesis)
    this.telemetryTimeoutMs = 45000;  // 45s for external telemetry adapters during cold start
    this.healthTimeoutMs = 8000;      // 8s for lightweight health checks
    this.wakeupTimeoutMs = 35000;     // 35s for cold-start wake-up trigger

    this.client = axios.create({
      baseURL: env.FASTAPI_INTERNAL_URL,
      timeout: this.workflowTimeoutMs,
      headers: {
        'Content-Type': 'application/json',
        'x-internal-service-secret': env.INTERNAL_SERVICE_SECRET || '',
      },
    });

    this.lastWakeupPing = 0;
    this.aiStatus = 'unknown';
    this.lastWakeupResult = null;
    this.isWakingUp = false;
  }

  /**
   * Determine if an error is transient (e.g. Render container spinning up from sleep).
   * 4xx client errors are NOT retryable.
   */
  _isRetryableError(error) {
    if (!error) return false;

    // Network errors (no HTTP response received)
    if (!error.response) {
      const code = error.code || '';
      return (
        code === 'ECONNRESET' ||
        code === 'ECONNREFUSED' ||
        code === 'ETIMEDOUT' ||
        code === 'ENOTFOUND' ||
        code === 'EAI_AGAIN' ||
        code === 'ECONNABORTED' ||
        error.message?.includes('timeout') ||
        error.message?.includes('Network Error') ||
        error.message?.includes('socket hang up')
      );
    }

    // Render cold-start / sleeping proxy status codes
    const status = error.response.status;
    return status === 502 || status === 503 || status === 504;
  }

  /**
   * Execute request with bounded exponential backoff retries for cold-start resilience.
   * Section 7: Max 3 retries, no infinite loop, no request storms, no retry on 4xx.
   */
  async _requestWithRetry(requestFn, options = {}) {
    const maxRetries = options.retries ?? 3;
    const baseDelayMs = options.delay ?? 2000;
    const operation = options.name ?? 'FastAPI operation';

    let lastError;
    for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        const isLastAttempt = attempt > maxRetries;
        const isRetryable = this._isRetryableError(error);

        if (isLastAttempt || !isRetryable) {
          break;
        }

        const delay = baseDelayMs * Math.pow(1.5, attempt - 1);
        logger.warn(
          {
            operation,
            attempt,
            maxRetries,
            delayMs: delay,
            statusCode: error.response?.status,
            errorCode: error.code,
            errorMessage: error.message,
          },
          'FastAPI AI service unavailable or starting up (Render cold-start detected); retrying...'
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    // If failed after retries due to cold start or network drop, raise structured AiServiceUnavailableError
    if (this._isRetryableError(lastError)) {
      throw new AiServiceUnavailableError(
        'The ORCA AI service is starting. Please retry shortly.',
        {
          operation,
          originalError: lastError.message,
          statusCode: lastError.response?.status || 503,
        }
      );
    }

    // Pass through detailed upstream error message if provided by Agent Core
    if (lastError.response?.data?.detail) {
      throw new UpstreamServiceError(
        `Agent Core error: ${JSON.stringify(lastError.response.data.detail)}`
      );
    }

    throw lastError;
  }

  /**
   * Dispatches an asynchronous non-blocking wake-up request to Python AI-services /health.
   * Debounced to avoid hammering the service if rapid connections or requests occur.
   * If the service is sleeping (e.g. Render cold start), this triggers the container spin-up immediately.
   */
  async triggerWakeup(source = 'manual') {
    const now = Date.now();
    // Debounce: don't send duplicate wake-up pings within 15 seconds if healthy or waking up
    if (this.isWakingUp || (now - this.lastWakeupPing < 15000 && this.aiStatus === 'healthy')) {
      logger.debug(
        { source, aiStatus: this.aiStatus },
        'FastAPI wake-up ping skipped (service recently checked or ping in flight)'
      );
      return this.lastWakeupResult || { status: this.aiStatus, source };
    }

    this.lastWakeupPing = now;
    this.isWakingUp = true;
    this.aiStatus = 'waking_up';

    logger.info(
      { source, url: `${env.FASTAPI_INTERNAL_URL}/health` },
      '🚀 Dispatched wake-up ping to Python AI Services (/health)'
    );

    try {
      const response = await this.client.get('/health', { timeout: this.wakeupTimeoutMs });
      this.isWakingUp = false;
      this.aiStatus = 'healthy';
      this.lastWakeupResult = {
        status: 'healthy',
        details: response.data,
        source,
        timestamp: new Date().toISOString(),
        latencyMs: Date.now() - now,
      };
      logger.info(
        {
          source,
          latencyMs: Date.now() - now,
          service: response.data?.service || 'orca-ai',
        },
        '✅ Python AI Services is awake and responding to health checks!'
      );
      return this.lastWakeupResult;
    } catch (error) {
      this.isWakingUp = false;
      const isCold = this._isRetryableError(error);
      this.aiStatus = isCold ? 'waking_up' : 'unreachable';
      this.lastWakeupResult = {
        status: this.aiStatus,
        source,
        error: error.message,
        isColdStart: isCold,
        timestamp: new Date().toISOString(),
      };
      if (isCold) {
        logger.warn(
          { source, err: error.message },
          '⏳ Python AI Services container is spinning up (cold-start in progress)...'
        );
      } else {
        logger.warn(
          { source, err: error.message, url: `${env.FASTAPI_INTERNAL_URL}/health` },
          '⚠️ Python AI Services health ping failed (service unreachable or starting)'
        );
      }
      return this.lastWakeupResult;
    }
  }

  async checkHealth() {
    const startTime = Date.now();
    try {
      const response = await this.client.get('/health', { timeout: this.healthTimeoutMs });
      this.aiStatus = 'healthy';
      return {
        status: 'healthy',
        latencyMs: Date.now() - startTime,
        details: response.data,
      };
    } catch (error) {
      const isCold = this._isRetryableError(error);
      this.aiStatus = isCold ? 'waking_up' : 'unreachable';
      logger.warn({ error: error.message, isCold }, 'FastAPI health check failed');
      // If it's cold, trigger a wake-up in background if not already started
      if (isCold && !this.isWakingUp) {
        this.triggerWakeup('checkHealth_cold_start').catch(() => {});
      }
      return {
        status: isCold ? 'cold_starting' : 'unreachable',
        details: error.response?.data || error.message,
      };
    }
  }

  async checkReady() {
    try {
      const response = await this.client.get('/ready', { timeout: this.healthTimeoutMs });
      return { status: 'ready', details: response.data };
    } catch (error) {
      return { status: 'unavailable', error: error.message };
    }
  }

  async executeWorkflow(request, requestId) {
    logger.info({ requestId }, 'Dispatching workflow execution to FastAPI agent core');
    const url = '/internal/ai/chat';
    const response = await this._requestWithRetry(
      () =>
        this.client.post(url, request, {
          headers: {
            'x-request-id': requestId,
          },
          timeout: this.workflowTimeoutMs,
        }),
      { name: 'executeWorkflow', retries: 3, delay: 2500 }
    );
    return response.data;
  }

  async executeMarineAnalysis(request, requestId) {
    const response = await this._requestWithRetry(
      () =>
        this.client.post('/internal/ai/analyze', request, {
          headers: { 'x-request-id': requestId },
          timeout: this.workflowTimeoutMs,
        }),
      { name: 'executeMarineAnalysis', retries: 2, delay: 2000 }
    );
    return response.data;
  }

  async executeRouteAnalysis(waypoints, vesselClass, bufferKm) {
    const response = await this._requestWithRetry(
      () =>
        this.client.post(
          '/internal/ai/route-analysis',
          {
            waypoints,
            vessel_class: vesselClass || 'motorized_fiberglass',
            buffer_km: bufferKm || 2.0,
          },
          { timeout: this.workflowTimeoutMs }
        ),
      { name: 'executeRouteAnalysis', retries: 2, delay: 2000 }
    );
    return response.data;
  }
  async executeRiskAnalysis(vesselClass, latitude, longitude) {
    const response = await this._requestWithRetry(
      () =>
        this.client.post(
          '/internal/ai/risk-analysis',
          {
            vessel_class: vesselClass,
            latitude,
            longitude,
          },
          { timeout: this.workflowTimeoutMs }
        ),
      { name: 'executeRiskAnalysis', retries: 2, delay: 2000 }
    );
    return response.data;
  }

  async executeSandbox(code, datasetCsv, contextData, timeoutSeconds) {
    const response = await this._requestWithRetry(
      () =>
        this.client.post(
          '/internal/ai/sandbox/execute',
          {
            code,
            dataset_csv: datasetCsv || null,
            context_data: contextData || {},
            timeout_seconds: timeoutSeconds || 10.0,
          },
          { timeout: (timeoutSeconds ? timeoutSeconds * 1000 : 15000) + 10000 }
        ),
      { name: 'executeSandbox', retries: 1, delay: 2000 }
    );
    return response.data;
  }

  async getRequestStatus(requestId) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get(`/internal/v1/orca/request/${encodeURIComponent(requestId)}`, {
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getRequestStatus', retries: 2, delay: 1500 }
      );
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  // ─── Direct Marine Scientific Telemetry Endpoints ─────────────────────────

  async getMarineWeather(latitude, longitude) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/internal/ai/marine/weather', {
            params: { latitude, longitude },
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getMarineWeather', retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine weather from FastAPI');
      return { status: 'unavailable', reason: 'Weather service temporarily unreachable' };
    }
  }

  async getOceanState(latitude, longitude) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/internal/ai/marine/ocean', {
            params: { latitude, longitude },
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getOceanState', retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch ocean state from FastAPI');
      return { status: 'unavailable', reason: 'Ocean state service temporarily unreachable' };
    }
  }

  async getPFZData(latitude, longitude) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/internal/ai/marine/pfz', {
            params: { latitude, longitude },
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getPFZData', retries: 2, delay: 2000 }
      );
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
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/internal/ai/marine/alerts', {
            params,
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getMarineAlerts', retries: 2, delay: 2000 }
      );
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
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/internal/ai/marine/zones', {
            params,
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getMarineZones', retries: 2, delay: 2000 }
      );
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
      const response = await this._requestWithRetry(
        () => this.client.get('/api/marine/map/config', { timeout: this.telemetryTimeoutMs }),
        { name: 'getMarineMapConfig', retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch marine map config from FastAPI');
      return { status: 'fallback', demo_mode: true, base_maps: [], marine_layers: [] };
    }
  }

  async getMarineLayer(layerName, params = {}) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get(`/api/marine/${layerName}`, {
            params,
            timeout: this.telemetryTimeoutMs,
          }),
        { name: `getMarineLayer:${layerName}`, retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message, layer: layerName }, 'Failed to fetch marine layer from FastAPI');
      return { type: 'FeatureCollection', features: [], status: 'unavailable', is_live: false };
    }
  }

  async getSatelliteObservations(latitude, longitude) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/satellite/observations', {
            params: { latitude, longitude },
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getSatelliteObservations', retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch satellite observations from FastAPI');
      return { status: 'unavailable', records: [], reason: 'Satellite service temporarily unreachable' };
    }
  }

  async getFishingZoneEstimate(latitude, longitude) {
    try {
      const response = await this._requestWithRetry(
        () =>
          this.client.get('/fishing-zone/estimate', {
            params: { latitude, longitude },
            timeout: this.telemetryTimeoutMs,
          }),
        { name: 'getFishingZoneEstimate', retries: 2, delay: 2000 }
      );
      return response.data;
    } catch (error) {
      logger.warn({ err: error.message }, 'Failed to fetch fishing-zone estimate from FastAPI');
      return { status: 'unavailable', data: null, reason: 'Fishing-zone estimate temporarily unreachable' };
    }
  }
}

export const fastApiClient = new FastApiClient();
