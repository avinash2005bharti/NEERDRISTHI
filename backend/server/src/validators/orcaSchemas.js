import { z } from 'zod';

export const locationInputSchema = z.object({
  name: z.string().max(200).optional(),
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
});

export const timeWindowInputSchema = z.object({
  start: z.string().datetime().optional(),
  end: z.string().datetime().optional(),
  label: z.string().max(100).optional(),
});

export const userProfileInputSchema = z.object({
  role: z.enum(['fisherman', 'authority', 'disaster_manager', 'admin']).default('fisherman'),
  vesselClass: z.string().max(100).optional(),
  language: z.string().max(20).default('en'),
});

export const geoJsonLineStringSchema = z.object({
  type: z.literal('LineString'),
  coordinates: z.array(
    z.tuple([
      z.number().min(-180).max(180), // Longitude
      z.number().min(-90).max(90),   // Latitude
    ])
  ).min(2),
});

export const orcaQuerySchema = z.object({
  conversationId: z.string().uuid().optional(),
  query: z.string().min(1, 'Query cannot be empty').max(2000),
  intent: z
    .enum(['safety_check', 'find_pfz', 'route_safety', 'marine_status', 'authority_monitoring'])
    .optional(),
  location: locationInputSchema.optional(),
  timeWindow: timeWindowInputSchema.optional(),
  userProfile: userProfileInputSchema.optional(),
  route: geoJsonLineStringSchema.optional(),
});
