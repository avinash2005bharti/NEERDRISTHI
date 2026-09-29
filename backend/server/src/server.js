import http from 'http';
import { createApp } from './app.js';
import { env, effectivePort, corsOriginsArray } from './config/env.js';
import { connectMongo, closeMongo } from './config/database.js';
import { initializeSockets } from './sockets/index.js';
import { logger } from './utils/logger.js';
import { fastApiClient } from './clients/fastApiClient.js';

async function bootstrap() {
  logger.info({ env: env.NODE_ENV }, 'Starting ORCA API Server...');

  // Initialize MongoDB connection (optional in local development)
  await connectMongo();

  const app = createApp();
  const server = http.createServer(app);

  // Initialize Socket.IO
  initializeSockets(server);

  server.listen(effectivePort, '0.0.0.0', () => {
    logger.info(
      {
        port: effectivePort,
        corsOrigins: corsOriginsArray,
        fastApiUrl: env.FASTAPI_INTERNAL_URL,
      },
      `ORCA API Server listening on http://0.0.0.0:${effectivePort}`
    );

    // Warm up / wake up Python AI services immediately when server starts
    fastApiClient.triggerWakeup('server_bootstrap').catch((err) => {
      logger.warn({ err: err?.message }, 'Initial background wake-up ping to Python AI services encountered note');
    });
  });

  // Graceful shutdown handling
  const shutdown = async (signal) => {
    logger.info({ signal }, 'Shutting down ORCA Server gracefully...');
    server.close(async () => {
      await closeMongo();
      logger.info('Server and DB closed cleanly. Exiting.');
      process.exit(0);
    });

    // Force shutdown after 10s if dangling connections
    setTimeout(() => {
      logger.error('Forcefully terminating process after timeout');
      process.exit(1);
    }, 10000);
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

bootstrap().catch((err) => {
  logger.fatal({ err }, 'Fatal error during Server startup');
  process.exit(1);
});
