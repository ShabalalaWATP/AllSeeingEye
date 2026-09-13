import { apiCall } from './client';
import {
  eventsResponseSchema,
  sourceHealthSchema,
  sourcesResponseSchema,
  storeStatsSchema,
} from './eventSchemas';
import type { Category, LiveEvent, Source, SourceHealth, StoreStats } from './eventSchemas';

export interface EventsQuery {
  categories?: readonly Category[];
  sources?: readonly string[];
  bbox?: readonly [number, number, number, number];
  country?: string;
  since?: string;
  limit?: number;
  military?: boolean;
  offset?: number;
  sampling?: 'newest' | 'geographic';
  timeBasis?: 'publication' | 'map_record_time';
}

export function eventsQueryString(query: EventsQuery): string {
  const params = new URLSearchParams();
  if (query.categories && query.categories.length > 0) {
    params.set('categories', query.categories.join(','));
  }
  if (query.sources?.length) params.set('sources', query.sources.join(','));
  if (query.bbox) params.set('bbox', query.bbox.join(','));
  if (query.country) params.set('country', query.country);
  if (query.since) params.set('since', query.since);
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  if (query.military !== undefined) params.set('military', String(query.military));
  if (query.offset !== undefined) params.set('offset', String(query.offset));
  if (query.sampling) params.set('sampling', query.sampling);
  if (query.timeBasis) params.set('time_basis', query.timeBasis);
  const text = params.toString();
  return text ? `?${text}` : '';
}

export async function fetchEvents(
  query: EventsQuery = {},
  signal?: AbortSignal,
): Promise<LiveEvent[]> {
  const page = await apiCall(`/api/events${eventsQueryString(query)}`, {
    schema: eventsResponseSchema,
    ...(signal ? { signal } : {}),
  });
  return page.items;
}

export function fetchStats(signal?: AbortSignal): Promise<StoreStats> {
  return apiCall('/api/events/stats', { schema: storeStatsSchema, ...(signal ? { signal } : {}) });
}

export async function fetchSources(): Promise<Source[]> {
  const page = await apiCall('/api/admin/sources', { schema: sourcesResponseSchema });
  return page.items;
}

export function resetSource(sourceId: string, signal?: AbortSignal): Promise<SourceHealth> {
  return apiCall(`/api/admin/sources/${encodeURIComponent(sourceId)}/reset`, {
    method: 'POST',
    schema: sourceHealthSchema,
    ...(signal ? { signal } : {}),
  });
}
