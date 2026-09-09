import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';
import type { Position } from '@/lib/map/geoJsonTypes';

export type TerrainElevations = components['schemas']['TerrainElevationsOut'];
export function fetchTerrainElevations(
  positions: readonly Position[],
  signal: AbortSignal,
): Promise<TerrainElevations> {
  return apiCall('/api/terrain/elevations', {
    method: 'POST',
    signal,
    body: { positions: positions.map(([lon, lat]) => ({ lon, lat })) },
    schema: z.object({
      elevations_m: z.array(z.number().min(-12000).max(10000)).length(positions.length),
      zoom: z.literal(10),
      resolution_m: z.number().positive().max(153),
      provider: z.literal('Mapzen Terrain Tiles'),
      attribution: z.string().min(1).max(2000),
      attribution_url: z.literal(
        'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      ),
      limitations: z.string().max(3000),
    }),
  });
}
