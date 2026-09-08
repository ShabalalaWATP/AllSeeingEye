/** Trackers: hazard and conflict boards computed from the live store, never stored. */
import { z } from 'zod';

import { liveEventSchema } from './eventSchemas';
import { apiCall } from './client';

export const activitySchema = z.object({
  last_24h: z.number().int(),
  last_7d: z.number().int(),
  previous_7d: z.number().int(),
  trend: z.number().nullable(),
});
export type Activity = z.infer<typeof activitySchema>;

export const dayBucketSchema = z.object({
  day: z.string(),
  count: z.number().int(),
  max_severity: z.number().nullable(),
});
export type DayBucket = z.infer<typeof dayBucketSchema>;

export const hazardCardSchema = z.object({
  hazard: z.string(),
  title: z.string(),
  activity: activitySchema,
  red_alerts: z.number().int(),
  max_severity: z.number().nullable(),
  countries: z.array(z.string()),
  latest: liveEventSchema.nullable(),
  top: liveEventSchema.nullable(),
});
export type HazardCard = z.infer<typeof hazardCardSchema>;

export const conflictSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  countries: z.array(z.string()),
  bbox: z.array(z.number()).length(4),
  belligerents: z.array(z.string()),
  keywords: z.array(z.string()),
  summary: z.string(),
});
export type Conflict = z.infer<typeof conflictSchema>;

export const conflictCardSchema = z.object({
  conflict: conflictSchema,
  activity: activitySchema,
  reporting_7d: z.number().int(),
  fatalities_7d: z.number().int().nonnegative().nullable().default(null),
  fatalities_upper_7d: z.number().int().nonnegative().nullable().default(null),
  fatalities_unknown_incidents: z.number().int().nonnegative().default(0),
  fatalities_disputed_incidents: z.number().int().nonnegative().default(0),
  other_activity_7d: z.number().int().nonnegative().default(0),
  unknown_date_reports: z.number().int().nonnegative().default(0),
  collapsed_reports_7d: z.number().int().nonnegative().default(0),
  max_severity: z.number().nullable(),
  latest: liveEventSchema.nullable(),
  top: liveEventSchema.nullable(),
});
export type ConflictCard = z.infer<typeof conflictCardSchema>;

export const hazardDetailSchema = z.object({
  card: hazardCardSchema,
  timeline: z.array(dayBucketSchema),
  events: z.array(liveEventSchema),
});
export type HazardDetail = z.infer<typeof hazardDetailSchema>;

export const conflictDetailSchema = z.object({
  card: conflictCardSchema,
  timeline: z.array(dayBucketSchema),
  events: z.array(liveEventSchema),
  evidence_groups: z
    .array(
      z.object({
        representative_id: z.string(),
        report_ids: z.array(z.string()),
        source_ids: z.array(z.string()),
        report_count: z.number().int().nonnegative(),
      }),
    )
    .default([]),
});
export type ConflictDetail = z.infer<typeof conflictDetailSchema>;

export const conflictSourceSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  status: z.enum(['configured', 'waiting', 'not_configured', 'healthy', 'degraded']),
  detail: z.string(),
  dataset_release: z.string().nullable(),
  last_success: z.string().nullable(),
});
export type ConflictSource = z.infer<typeof conflictSourceSchema>;

export async function fetchConflictSources(): Promise<ConflictSource[]> {
  const page = await apiCall('/api/trackers/conflict-sources', {
    schema: z.object({ items: z.array(conflictSourceSchema) }),
  });
  return page.items;
}

export async function fetchDisasterBoard(): Promise<HazardCard[]> {
  const page = await apiCall('/api/trackers/disasters', {
    schema: z.object({ items: z.array(hazardCardSchema) }),
  });
  return page.items;
}

export async function fetchDisasterDetail(hazard: string): Promise<HazardDetail> {
  return apiCall(`/api/trackers/disasters/${encodeURIComponent(hazard)}`, {
    schema: hazardDetailSchema,
  });
}

export async function fetchConflictBoard(): Promise<ConflictCard[]> {
  const page = await apiCall('/api/trackers/conflicts', {
    schema: z.object({ items: z.array(conflictCardSchema) }),
  });
  return page.items;
}

export async function fetchConflictDetail(id: string): Promise<ConflictDetail> {
  return apiCall(`/api/trackers/conflicts/${encodeURIComponent(id)}`, {
    schema: conflictDetailSchema,
  });
}
