import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import { corsOriginsArray } from './config/env.js';
import { httpLogger } from './middleware/logging.js';
import { apiRateLimiter } from './middleware/rateLimiter.js';
import { errorHandler } from './middleware/errorHandler.js';
import { apiRouter } from './routes/index.js';
import { healthRouter } from './routes/health.js';
import { NotFoundError } from './utils/errors.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function createApp() {
  const app = express();

  // 1. Security Headers (disable CSP to allow Leaflet CDN, Google Fonts, and OSM map tiles)
  app.use(
    helmet({
      contentSecurityPolicy: false,
    })
  );

  // 2. CORS configuration restricted to configured origins
  app.use(
    cors({
      origin: (origin, callback) => {
        // Allow requests with no origin (like mobile apps, curl, server-to-server)
        if (!origin) return callback(null, true);
        if (
          corsOriginsArray.includes('*') ||
          corsOriginsArray.includes(origin) ||
          /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)
        ) {
          return callback(null, true);
        }
        return callback(new Error(`CORS policy does not allow access from origin: ${origin}`));
      },
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'x-request-id'],
    })
  );

  // 3. Body parsers with request size limits
  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: true, limit: '2mb' }));

  // 4. Structured HTTP Logging
  app.use(httpLogger);

  // 5. Rate limiting for API endpoints
  app.use('/api', apiRateLimiter);

  // 6. Base health & API Routes
  app.use(healthRouter);
  app.use('/api/v1', apiRouter);

  // 7. Serve Static Frontend Client (SPA)
  const candidateDistPaths = [
    path.resolve(__dirname, '../public'),
    path.resolve(__dirname, '../dist'),
    path.resolve(__dirname, '../../../frontend/dist'),
    path.resolve(process.cwd(), 'public'),
    path.resolve(process.cwd(), 'dist'),
  ];
  const clientDistPath = candidateDistPaths.find((p) => fs.existsSync(path.join(p, 'index.html')));

  if (clientDistPath) {
    app.use(express.static(clientDistPath));

    // Handle SPA client-side routes (e.g. /home, /map, /alerts, /profile, /history)
    app.get('*', (req, res, next) => {
      // Do not intercept unhandled /api or /socket.io requests
      if (req.path.startsWith('/api') || req.path.startsWith('/socket.io')) {
        return next();
      }
      res.sendFile(path.join(clientDistPath, 'index.html'));
    });
  }

  // 8. Catch-all 404 handler for unhandled API requests or missing resources
  app.use((req, _res, next) => {
    next(new NotFoundError(`Resource not found at ${req.method} ${req.originalUrl}`));
  });

  // 9. Centralized error handler
  app.use(errorHandler);

  return app;
}

