import { z } from 'zod';

import { apiCall } from './client';
import type { components, paths } from './types.gen';

export type NavigationRoute = components['schemas']['NavigationRouteOut'];
export type NavigationRequest =
  paths['/api/navigation/route']['post']['requestBody']['content']['application/json'];
export type NavigationCapabilities = components['schemas']['NavigationCapabilitiesOut'];

const point = z.tuple([z.number().min(-180).max(180), z.number().min(-90).max(90)]);
export const navigationRouteSchema = z.object({
  mode: z.enum(['driving', 'walking', 'cycling']),
  distance_km: z.number().min(0).max(5000),
  duration_seconds: z.number().min(0).max(604800),
  coordinates: z.array(point).min(2).max(20000),
  steps: z
    .array(
      z.object({
        instruction: z.string().min(1).max(500),
        distance_km: z.number().min(0).max(5000),
        duration_seconds: z.number().min(0).max(604800),
      }),
    )
    .min(1)
    .max(500),
  provider: z.literal('FOSSGIS Valhalla'),
  attribution: z.string().max(500),
  limitations: z.string().max(1000),
});

export function calculateNavigationRoute(
  body: NavigationRequest,
  signal: AbortSignal,
): Promise<NavigationRoute> {
  return apiCall('/api/navigation/route', {
    method: 'POST',
    body,
    signal,
    schema: navigationRouteSchema,
  });
}

export function fetchNavigationCapabilities(signal: AbortSignal): Promise<NavigationCapabilities> {
  return apiCall('/api/navigation/capabilities', {
    signal,
    schema: z.object({
      provider: z.string().max(100),
      operator_contact: z.string().max(254),
      available: z.boolean(),
      configuration_message: z.string().max(1000).nullable().default(null),
      privacy: z.string().max(1000),
    }),
  });
}
