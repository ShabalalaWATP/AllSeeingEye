/**
 * The documented sustained-stream fixture for KAN-81: a full 5,000-record mirror of mixed
 * located categories, then repeated 250-record stream batches. Kept deterministic so
 * before/after figures compare like with like.
 */
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { SseMessage } from '@/lib/sse';

import { liveEvent } from './fixtures';

export const FIXTURE_MIRROR_SIZE = 5_000;
export const FIXTURE_BATCH_SIZE = 250;
export const FIXTURE_BATCHES = 20;

const KINDS = [
  { category: 'disaster', subtype: 'earthquake', source_id: 'usgs_earthquakes' },
  { category: 'aviation', subtype: 'aircraft_position', source_id: 'opensky' },
  { category: 'maritime', subtype: 'vessel_position', source_id: 'aisstream' },
  { category: 'news', subtype: 'article', source_id: 'gdelt' },
  { category: 'conflict', subtype: 'battle', source_id: 'ucdp' },
] as const;

/** A located record whose time and kind derive from its sequence number. */
export function streamEvent(sequence: number, base: number, overrides: Partial<LiveEvent> = {}) {
  const kind = KINDS[sequence % KINDS.length]!;
  const at = new Date(base + sequence * 1_000).toISOString();
  return liveEvent({
    id: `s${sequence}`,
    ...kind,
    title: `Stream record ${sequence}`,
    published_at: at,
    observed_at: at,
    point: { lon: ((sequence * 137.508) % 360) - 180, lat: ((sequence * 37.2) % 170) - 85 },
    country_iso: null,
    tags: [],
    attributes: {},
    ...overrides,
  });
}

export function upsertMessage(events: readonly LiveEvent[]): SseMessage {
  return { event: 'event.upsert', id: null, data: JSON.stringify({ events }) };
}

export function expireMessage(ids: readonly string[]): SseMessage {
  return { event: 'event.expire', id: null, data: JSON.stringify({ ids, count: ids.length }) };
}

export function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2;
}
