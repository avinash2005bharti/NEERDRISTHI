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
        },
      },
    });
  }
}

export const healthController = new HealthController();
