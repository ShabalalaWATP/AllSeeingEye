import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type NavigationPlace = components['schemas']['NavigationPlaceOut'];

export function searchNavigationPlaces(
  query: string,
  signal: AbortSignal,
): Promise<NavigationPlace[]> {
  return apiCall('/api/navigation/places', {
    method: 'POST',
    body: { query },
    signal,
    schema: z
      .array(
        z.object({
          label: z.string().min(1).max(1000),
          lat: z.number().min(-90).max(90),
          lon: z.number().min(-180).max(180),
        }),
      )
      .max(5),
  });
}
