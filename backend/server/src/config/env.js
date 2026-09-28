import dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().optional(),
  GATEWAY_PORT: z.coerce.number().default(3001),
  CORS_ORIGINS: z.string().default('http://localhost:3000,http://localhost:5173'),
  FRONTEND_URL: z.string().optional(),
  MONGODB_URI: z.string().optional().default(''),
  MONGODB_DB_NAME: z.string().default('orca'),
  JWT_SECRET: z.string().optional().default(''),
  JWT_EXPIRES_IN: z.string().default('7d'),
  BCRYPT_SALT_ROUNDS: z.coerce.number().default(12),
  AI_SERVICE_URL: z.string().url().optional(),
  FASTAPI_INTERNAL_URL: z.string().url().default('http://localhost:8000'),
  INTERNAL_SERVICE_SECRET: z.string().optional().default(''),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace']).default('info'),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().default(900000), // 15 mins
  RATE_LIMIT_MAX_REQUESTS: z.coerce.number().default(100),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('Invalid environment variables in Server:', parsed.error.format());
  process.exit(1);
}

export const env = parsed.data;

// Normalize AI service URL: AI_SERVICE_URL takes precedence if specified (Render convention)
if (env.AI_SERVICE_URL) {
  env.FASTAPI_INTERNAL_URL = env.AI_SERVICE_URL;
}

// Compute effective port (Render provides process.env.PORT)
export const effectivePort = env.PORT || env.GATEWAY_PORT || 3001;

// CORS Origins array computation (merges CORS_ORIGINS with FRONTEND_URL if provided)
const rawOrigins = env.CORS_ORIGINS.split(',').map((origin) => origin.trim()).filter(Boolean);
if (env.FRONTEND_URL) {
  const normalizedFrontendUrl = env.FRONTEND_URL.trim().replace(/\/+$/, '');
  if (!rawOrigins.includes(normalizedFrontendUrl)) {
    rawOrigins.push(normalizedFrontendUrl);
  }
}
export const corsOriginsArray = rawOrigins;

