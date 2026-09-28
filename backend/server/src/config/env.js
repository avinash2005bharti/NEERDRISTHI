import dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  GATEWAY_PORT: z.coerce.number().default(3001),
  CORS_ORIGINS: z.string().default('http://localhost:3000,http://localhost:5173'),
  MONGODB_URI: z.string().optional().default(''),
  MONGODB_DB_NAME: z.string().default('orca'),
  JWT_SECRET: z.string().optional().default(''),
  JWT_EXPIRES_IN: z.string().default('7d'),
  BCRYPT_SALT_ROUNDS: z.coerce.number().default(12),
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

export const corsOriginsArray = env.CORS_ORIGINS.split(',').map((origin) => origin.trim());
