import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { reportJobSchema } from './reportJobs';
import type { components } from './types.gen';

export type CyberSnapshot = components['schemas']['CyberSnapshotOut'];
export type CyberItem = components['schemas']['CyberItemOut'];
export type CyberActors = components['schemas']['CyberActorsOut'];
export type CyberActor = components['schemas']['CyberActorOut'];
export type CyberBriefing = components['schemas']['CyberBriefingOut'];
export type CyberDays = CyberBriefing['window_days'];
export type CyberTheme = CyberItem['themes'][number];
export type CyberThemeTally = CyberSnapshot['themes'][number];
export type CyberStateTally = CyberSnapshot['state_mentions'][number];
const radarAttackCountrySchema = z.object({
  country_iso: z.string().regex(/^[A-Z]{2}$/),
  country_name: z.string().min(1).max(80),
  rank: z.number().int().positive(),
  share_percent: z.number().min(0).max(100),
});
const radarAttackSchema = z.object({
  status: z.enum(['ready', 'partial', 'stale', 'unavailable', 'not_configured', 'disabled']),
  fetched_at: z.iso.datetime({ offset: true }).nullable(),
  layers: z
    .array(
      z.object({
        layer: z.enum(['layer3', 'layer7']),
        period_from: z.iso.datetime({ offset: true }),
        period_to: z.iso.datetime({ offset: true }),
        updated_at: z.iso.datetime({ offset: true }).nullable(),
        unit: z.enum(['bytes', 'requests']),
        countries: z.array(radarAttackCountrySchema).max(10),
      }),
    )
    .max(2),
  source_url: z.url(),
});
export type RadarAttackSnapshot = z.infer<typeof radarAttackSchema>;
export const fetchRadarAttackTrends = (signal?: AbortSignal) =>
  apiCall('/api/cyber/radar-attacks', { schema: radarAttackSchema, ...(signal ? { signal } : {}) });
export const CYBER_PERIODS = [2, 5, 7, 14, 30] as const;
export const parseCyberDays = (value: string | null): CyberDays =>
  CYBER_PERIODS.find((day) => String(day) === value) ?? 2;

const date = z.iso.datetime({ offset: true });
const daysSchema = z.union([
  z.literal(2),
  z.literal(5),
  z.literal(7),
  z.literal(14),
  z.literal(30),
]);
const kindSchema = z.enum([
  'ransomware_claim',
  'outage_signal',
  'known_exploited_vulnerability',
  'advisory',
  'threat_report',
  'news_report',
  'other',
]);
export const CYBER_THEMES = [
  'nation_state',
  'nato_allies',
  'uk_infrastructure',
  'ukraine',
  'gnss_interference',
  'critical_infrastructure',
] as const;
const themeSchema = z.enum(CYBER_THEMES);
const counts = z
  .array(z.object({ kind: kindSchema, count: z.number().int().nonnegative() }))
  .max(7);
const itemSchema = z.object({
  id: z.string(),
  kind: kindSchema,
  title: z.string(),
  summary: z.string().nullable(),
  url: z.string(),
  source_id: z.string(),
  source_name: z.string(),
  organisation: z.string(),
  published_at: date,
  observed_at: date,
  country_iso: z.string().nullable(),
  grade: z.string(),
  actor_mentions: z.array(z.object({ group_id: z.string(), matched_name: z.string() })).max(300),
  kev: z
    .object({
      cve: z.string(),
      vendor: z.string(),
      product: z.string(),
      date_added: z.string(),
      due_date: z.string(),
      ransomware_use: z.string(),
      cwes: z.string(),
      required_action: z.string(),
    })
    .nullable(),
  themes: z.array(themeSchema).max(6),
});
const snapshotSchema: z.ZodType<CyberSnapshot> = z.object({
  as_of: date,
  window_days: daysSchema,
  period_from: date,
  period_to: date,
  coverage_note: z.string(),
  retained_count: z.number().int().nonnegative().max(10_000),
  returned_count: z.number().int().nonnegative().max(200),
  truncated: z.boolean(),
  counts,
  timeline: z
    .array(z.object({ day: z.string(), total: z.number().int().nonnegative(), counts }))
    .max(31),
  themes: z
    .array(
      z.object({
        theme: themeSchema,
        count: z.number().int().nonnegative(),
        daily: z.array(z.number().int().nonnegative()).max(31),
      }),
    )
    .max(6),
  state_mentions: z
    .array(
      z.object({
        state: z.string().max(60),
        count: z.number().int().nonnegative(),
        group_ids: z.array(z.string().regex(/^G\d{4}$/)).max(12),
      }),
    )
    .max(20),
  top_countries: z
    .array(z.object({ key: z.string(), count: z.number().int().nonnegative() }))
    .max(250),
  actor_mentions: z
    .array(
      z.object({ group_id: z.string(), name: z.string(), count: z.number().int().nonnegative() }),
    )
    .max(300),
  sources: z
    .array(
      z.object({
        source_id: z.string(),
        name: z.string(),
        organisation: z.string(),
        url: z.string(),
        status: z.enum(['idle', 'healthy', 'degraded', 'disabled']),
        last_success: date.nullable(),
        last_error_at: date.nullable(),
        retained_count: z.number().int().nonnegative(),
      }),
    )
    .max(100),
  items: z.array(itemSchema).max(200),
});
const actorSchema = z.object({
  group_id: z.string().regex(/^G\d{4}$/),
  name: z.string(),
  associated_names: z.array(z.string()).max(80),
  description: z.string(),
  url: z.string(),
  modified_at: date,
  technique_ids: z.array(z.string().regex(/^T\d{4}(\.\d{3})?$/)).max(1000),
  technique_count: z.number().int().nonnegative(),
  state_association: z.string().max(60).nullable(),
});
const actorsSchema: z.ZodType<CyberActors> = z.object({
  available: z.boolean(),
  coverage_note: z.string(),
  catalogue: z
    .object({
      source_id: z.string(),
      version: z.string(),
      released_at: date,
      retrieved_at: date,
      source_url: z.string(),
      source_sha256: z.string(),
      licence_url: z.string(),
      attribution: z.string(),
      limitations: z.string(),
      actors: z.array(actorSchema).max(300),
    })
    .nullable(),
});
const hasPeriod = (
  value: { window_days: number; period_from: string; period_to: string },
  days: number,
) =>
  value.window_days === days &&
  Date.parse(value.period_to) - Date.parse(value.period_from) === days * 86_400_000;

export const fetchCyberSnapshot = (days: CyberDays, signal?: AbortSignal) =>
  apiCall(`/api/cyber?days=${days}`, {
    ...(signal ? { signal } : {}),
    schema: snapshotSchema.refine(
      (value) => hasPeriod(value, days) && value.returned_count === value.items.length,
    ),
  });
export const fetchCyberActors = () => apiCall('/api/cyber/actors', { schema: actorsSchema });
export function ensureCyberBriefing(days: CyberDays, signal: AbortSignal): Promise<CyberBriefing> {
  const schema: z.ZodType<CyberBriefing> = z
    .object({
      job: reportJobSchema,
      next_refresh_at: date,
      coverage_note: z.string(),
      window_days: daysSchema,
      period_from: date,
      period_to: date,
    })
    .refine((value) => hasPeriod(value, days));
  return scopedMutation(() =>
    apiCall(`/api/cyber/briefing?days=${days}`, {
      method: 'POST',
      schema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
