import { z } from 'zod';

export const registerSchema = z.object({
  email: z.string().email('Invalid email address').max(255),
  password: z.string().min(6, 'Password must be at least 6 characters long').max(128),
  name: z.string().min(2, 'Name must be at least 2 characters long').max(100),
  role: z.enum(['fisherman', 'authority', 'disaster_manager', 'admin']).default('fisherman'),
  vesselClass: z.string().max(100).optional(),
  preferredLanguage: z.string().max(10).default('en'),
});

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});
