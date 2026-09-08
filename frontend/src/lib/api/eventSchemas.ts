/**
 * Response schemas for the live event store, the stream and the source registry,
 * derived from the backend's EventOut, StoreStatsOut and SourceOut models.
 */
import { z } from 'zod';
import type { components } from './types.gen';
import { sourceDateSchema, textTransformationSchema } from './sourceProvenance';

export const categorySchema = z.enum([
  'news',
  'conflict',
  'disaster',
  'aviation',
  'maritime',
  'space',
  'cyber',
  'social',
  'political',
  'humanitarian',
  'economic',
]);
export type Category = z.infer<typeof categorySchema>;
export const CATEGORIES: readonly Category[] = categorySchema.options;

export const pointSchema = z.object({ lon: z.number(), lat: z.number() });

const scalarSchema = z.union([z.string(), z.number(), z.boolean(), z.null()]);

export const liveEventSchema = z.object({
  transformations: z.array(textTransformationSchema).default([]),
  source_dates: z.array(sourceDateSchema).default([]),
  id: z.string(),
  source_id: z.string(),
  category: categorySchema,
  subtype: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  url: z.string().nullable(),
  published_at: z.string().nullable(),
  observed_at: z.string(),
  language: z.string(),
  title_en: z.string().nullable(),
  point: pointSchema.nullable(),
  geo_confidence: z.enum(['exact', 'city', 'admin1', 'country', 'none']),
  country_iso: z.string().nullable(),
  tags: z.array(z.string()),
  severity: z.number().nullable(),
  reliability: z.enum(['A', 'B', 'C', 'D', 'E', 'F']),
  credibility: z.number().int(),
  grade: z.string(),
  grade_rationale: z.string(),
  story_id: z.string().nullable(),
  attributes: z.record(z.string(), scalarSchema),
});
export type LiveEvent = components['schemas']['EventOut'];

export const eventsResponseSchema = z.object({
  items: z.array(liveEventSchema),
  count: z.number().int(),
});

export const storeStatsSchema = z.object({
  total: z.number().int(),
  estimated_bytes: z.number().int(),
  budget_bytes: z.number().int(),
  per_category: z.array(
    z.object({
      category: categorySchema,
      count: z.number().int(),
      oldest: z.string().nullable(),
      newest: z.string().nullable(),
    }),
  ),
});
export type StoreStats = z.infer<typeof storeStatsSchema>;

export const sourceHealthSchema = z.object({
  source_id: z.string(),
  status: z.enum(['idle', 'healthy', 'degraded', 'disabled']),
  last_success: z.string().nullable(),
  last_error: z.string().nullable(),
  last_error_at: z.string().nullable(),
  consecutive_failures: z.number().int(),
  items_last_poll: z.number().int(),
  last_latency_ms: z.number().nullable(),
  next_poll_at: z.string().nullable(),
  polls: z.number().int(),
});
export type SourceHealth = z.infer<typeof sourceHealthSchema>;

export const sourceSchema = z.object({
  enabled: z.boolean().optional(),
  test_available: z.boolean().optional(),
  environment_disabled: z.boolean().optional(),
  id: z.string(),
  name: z.string(),
  organisation: z.string(),
  category: categorySchema,
  kind: z.string(),
  url: z.string(),
  reliability: z.enum(['A', 'B', 'C', 'D', 'E', 'F']),
  poll_interval_seconds: z.number().int(),
  language: z.string(),
  licence_note: z.string(),
  homepage: z.string(),
  requires_key: z.boolean(),
  instrument: z.boolean(),
  flags: z.array(z.string()),
  health: sourceHealthSchema,
});
export type Source = z.infer<typeof sourceSchema>;

export const sourcesResponseSchema = z.object({ items: z.array(sourceSchema) });

/** Payloads carried by the server-sent events on /api/stream. */
export const streamUpsertSchema = z.object({
  source_id: z.string().nullable().optional(),
  events: z.array(liveEventSchema),
});
export const streamExpireSchema = z.object({ ids: z.array(z.string()), count: z.number().int() });
export const streamResyncSchema = z.object({ reason: z.enum(['expiry_overflow', 'stream_gap']) });
