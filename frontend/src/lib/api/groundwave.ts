import { z } from 'zod';
import { apiCall } from './client';
import type { components, paths } from './types.gen';

export type GroundwaveResult = components['schemas']['GroundwaveOut'];
export type GroundwaveRequest = NonNullable<
  paths['/api/radio/groundwave']['post']['requestBody']
>['content']['application/json'];
export function calculateGroundwave(
  body: GroundwaveRequest,
  signal: AbortSignal,
): Promise<GroundwaveResult> {
  return apiCall('/api/radio/groundwave', {
    method: 'POST',
    body,
    signal,
    schema: z.object({
      model: z.literal('NTIA LFMF 1.1 (P.368-10)'),
      status: z.literal('calculated'),
      samples: z
        .array(
          z.object({
            distance_km: z.number().min(1).max(200),
            basic_transmission_loss_db: z.number(),
            native_reference_field_dbuv_m: z.number(),
            received_power_dbm: z.number(),
            method: z.enum(['flat_earth', 'residue_series']),
          }),
        )
        .min(2)
        .max(64)
        .length(body.sample_count ?? 48)
        .refine(
          (samples) =>
            samples.every(
              (sample, index) =>
                index === 0 || sample.distance_km > (samples[index - 1]?.distance_km ?? Infinity),
            ),
          'Groundwave distances must increase strictly.',
        )
        .refine(
          (samples) =>
            samples[0]?.distance_km === 1 &&
            Math.abs((samples.at(-1)?.distance_km ?? NaN) - (body.max_distance_km ?? 200)) <= 1e-6,
          'Groundwave distances must span the requested range.',
        ),
      source_url: z.literal('https://github.com/NTIA/LFMF/tree/v1.1'),
      limitations: z.string().max(5000),
    }),
  });
}
