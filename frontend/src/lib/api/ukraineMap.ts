/** Provider frontline geometry and spotted losses: reported, flagged and stamped, never fact. */
import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type UkraineFrontline = components['schemas']['FrontlineOut'];
export type FrontlineFeature = components['schemas']['FrontlineFeatureOut'];
export type FrontlineKind = components['schemas']['FrontlineKind'];
export type FrontlineStatus = components['schemas']['FrontlineStatus'];
export type UkraineSpotted = components['schemas']['SpottedOut'];
export type SpottedLoss = components['schemas']['SpottedLossOut'];

const statusSchema = z.enum(['disabled', 'ready', 'stale', 'unavailable']);
const point = z.tuple([z.number(), z.number()]);
const polygons = z.array(z.array(z.array(point).max(20000)).max(50)).max(400);
const lines = z.array(z.array(point).max(20000)).max(400);

export const ukraineFrontlineSchema: z.ZodType<UkraineFrontline> = z.object({
  status: statusSchema,
  reason: z.string().max(600),
  provider: z.string().max(40).nullable(),
  attribution: z.string().max(200).nullable(),
  terms: z.string().max(400).nullable(),
  assessed_at: z.string().max(40).nullable(),
  downloaded_at: z.string().nullable(),
  features: z
    .array(
      z.object({
        kind: z.enum(['occupied', 'liberated', 'unknown', 'historical', 'line']),
        label: z.string().max(120),
        polygons,
        lines,
      }),
    )
    .max(400),
});

export const ukraineSpottedSchema: z.ZodType<UkraineSpotted> = z.object({
  status: statusSchema,
  reason: z.string().max(600),
  attribution: z.string().max(200),
  downloaded_at: z.string().nullable(),
  losses: z
    .array(
      z.object({
        id: z.number().int(),
        lat: z.number().min(-90).max(90),
        lon: z.number().min(-180).max(180),
        model: z.string().max(80),
        equipment_type: z.string().max(60),
        status: z.string().max(30),
        lost_by: z.string().max(20),
        on: z.string(),
        place: z.string().max(120),
      }),
    )
    .max(3000),
});

export function fetchUkraineFrontline(signal?: AbortSignal): Promise<UkraineFrontline> {
  return apiCall(
    '/api/conflicts/ukraine/frontline',
    signal ? { schema: ukraineFrontlineSchema, signal } : { schema: ukraineFrontlineSchema },
  );
}

export function fetchUkraineSpotted(signal?: AbortSignal): Promise<UkraineSpotted> {
  return apiCall(
    '/api/conflicts/ukraine/spotted',
    signal ? { schema: ukraineSpottedSchema, signal } : { schema: ukraineSpottedSchema },
  );
}

export const FRONTLINE_KIND_LABELS: Record<FrontlineKind, string> = {
  occupied: 'Provider: occupied',
  liberated: 'Provider: liberated',
  unknown: 'Provider: status unknown',
  historical: 'Provider: occupied before 2022',
  line: 'Provider: front line',
};
