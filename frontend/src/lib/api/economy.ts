import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type EconomySnapshot = components['schemas']['EconomySnapshotOut'];
export type EconomySeries = components['schemas']['EconomySeriesOut'];
export type EconomyRegion = components['schemas']['EconomyRegionOut'];
export type EconomyNews = components['schemas']['EconomyNewsOut'];
export type EconomyNewsItem = components['schemas']['EconomyNewsItemOut'];

const seriesSchema = z.object({
  id: z.string(),
  name: z.string(),
  unit: z.string(),
  frequency: z.enum(['annual', 'daily']),
  provider: z.string(),
  source_url: z.string(),
  status: z.enum(['available', 'stale', 'unavailable']),
  note: z.string(),
  updated_at: z.iso.datetime({ offset: true }).nullable(),
  source_updated_at: z.string().nullable(),
  points: z.array(z.object({ date: z.string(), value: z.number().nullable() })).max(90),
});
const snapshotSchema: z.ZodType<EconomySnapshot> = z.object({
  fetched_at: z.iso.datetime({ offset: true }),
  refresh_after: z.iso.datetime({ offset: true }),
  regions: z
    .array(z.object({ id: z.string(), name: z.string(), series: z.array(seriesSchema).max(12) }))
    .max(6),
  fx: z.array(seriesSchema).max(5),
});
const newsSchema: z.ZodType<EconomyNews> = z.object({
  as_of: z.iso.datetime({ offset: true }),
  window_hours: z.number().int().positive(),
  coverage_note: z.string(),
  items: z
    .array(
      z.object({
        id: z.string(),
        title: z.string(),
        url: z.string(),
        source_id: z.string(),
        source_name: z.string(),
        organisation: z.string(),
        published_at: z.iso.datetime({ offset: true }),
        region_codes: z.array(z.enum(['GB', 'US', 'RU', 'CN', 'IR'])),
        viewpoint: z.enum(['official_issuer', 'state_aligned', 'publisher']),
      }),
    )
    .max(100),
});

export const fetchEconomy = () => apiCall('/api/economy', { schema: snapshotSchema });
export const fetchEconomyNews = () => apiCall('/api/economy/news', { schema: newsSchema });
