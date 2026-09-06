import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import type { components } from './types.gen';
export type FootprintQuery = components['schemas']['FootprintSearchIn'];
export type FootprintCollection = components['schemas']['FootprintCollectionOut'];
const position = z.tuple([z.number(), z.number()]);
const schema: z.ZodType<FootprintCollection> = z.object({
  type: z.literal('FeatureCollection'),
  status: z.enum(['completed', 'empty', 'unavailable']),
  features: z
    .array(
      z.object({
        type: z.literal('Feature'),
        id: z.string(),
        geometry: z.object({
          type: z.literal('MultiPolygon'),
          coordinates: z.array(z.array(z.array(position))),
        }),
        properties: z.object({
          collection: z.string(),
          captured_at: z.string(),
          cloud_cover: z.number().nullable(),
          source_url: z.string(),
          licence: z.string(),
          licence_url: z.string(),
        }),
      }),
    )
    .max(20),
  truncated: z.boolean(),
  limitations: z.string(),
  queried_at: z.string(),
});
export function searchFootprints(body: FootprintQuery, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/research/footprints', { method: 'POST', body, signal, schema }),
  );
}
