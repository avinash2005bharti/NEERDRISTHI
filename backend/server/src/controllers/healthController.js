import { getDb } from '../config/database.js';
import { fastApiClient } from '../clients/fastApiClient.js';
import { env } from '../config/env.js';

export class HealthController {
  async getHealth(_req, res) {
    const db = getDb();
    const mongoStatus = db ? 'connected' : env.MONGODB_URI ? 'disconnected' : 'unconfigured';

    const agentCoreHealth = await fastApiClient.checkHealth();

    res.status(200).json({
      status: 'ok',
      service: 'orca-gateway',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      components: {
        database: {
          type: 'mongodb',
          status: mongoStatus,
        },
        agentCore: {
          url: env.FASTAPI_INTERNAL_URL,
          status: agentCoreHealth.status,
          latencyMs: agentCoreHealth.latencyMs,
          details: agentCoreHealth.details,
        },
      },
    });
  }

  async getAiHealth(_req, res) {
    const agentCoreHealth = await fastApiClient.checkHealth();
    res.status(agentCoreHealth.status === 'healthy' ? 200 : 503).json({
      service: 'orca-ai',
      url: env.FASTAPI_INTERNAL_URL,
      ...agentCoreHealth,
      timestamp: new Date().toISOString(),
    });
  }

  async wakeupAi(req, res) {
    const source = req.query.source || req.body?.source || 'frontend_connect';
    // Non-blocking background trigger to wake up Python AI services
    fastApiClient.triggerWakeup(source).catch(() => {});

    res.status(202).json({
      message: 'Python AI services wake-up request dispatched',
      targetUrl: `${env.FASTAPI_INTERNAL_URL}/health`,
      currentStatus: fastApiClient.aiStatus,
      source,
      timestamp: new Date().toISOString(),
    });
  }

  async getReady(_req, res) {
    const readyStatus = await fastApiClient.checkReady();
    res.status(200).json({
      status: 'ready',
      gateway: 'ok',
      agentCore: readyStatus,
      timestamp: new Date().toISOString(),
    });
  }
}

export const healthController = new HealthController();
