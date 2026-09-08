import { isSatellite, satellitePriority } from '@/lib/satellites';
import type { LiveEvent } from '@/lib/api/eventSchemas';

export const MARITIME_SNAPSHOT_LIMIT = 1_500;
export const RESERVED_VESSELS = 1_500;
export const SATELLITE_SNAPSHOT_LIMIT = 1_500;
export const RESERVED_SATELLITES = 1_500;
export const FIRMS_SNAPSHOT_LIMIT = 1_000;
export const RESERVED_FIRMS = 1_000;

export function isFirms(event: LiveEvent): boolean {
  return (
    event.category === 'disaster' &&
    event.subtype === 'thermal_detection' &&
    (event.source_id === 'firms' || event.source_id.startsWith('firms_'))
  );
}

function observationOrder(a: LiveEvent, b: LiveEvent): number {
  return (
    Date.parse(a.observed_at) - Date.parse(b.observed_at) ||
    Date.parse(a.published_at ?? a.observed_at) - Date.parse(b.published_at ?? b.observed_at)
  );
}

/** Keep the newer copy when a vessel appears in both asynchronous snapshots. */
export function mergeSnapshots(main: LiveEvent[], maritime: LiveEvent[]): Map<string, LiveEvent> {
  const merged = new Map(main.map((event) => [event.id, event]));
  for (const event of maritime) {
    const previous = merged.get(event.id);
    if (!previous || observationOrder(event, previous) >= 0) merged.set(event.id, event);
  }
  return merged;
}

/** Reserve ships and satellites, favouring specific public catalogues over bulk active data. */
export function boundedEvents(
  byId: Record<string, LiveEvent>,
  limit: number,
): Record<string, LiveEvent> {
  const events = Object.values(byId);
  if (events.length <= limit) return byId;
  events.sort((a, b) => observationOrder(b, a) || a.id.localeCompare(b.id));
  const reserved = events
    .filter((event) => event.category === 'maritime' && event.subtype === 'vessel_position')
    .slice(0, Math.min(RESERVED_VESSELS, limit));
  const satellites = events
    .filter(isSatellite)
    .sort((a, b) => satellitePriority(b) - satellitePriority(a) || observationOrder(b, a))
    .slice(0, Math.min(RESERVED_SATELLITES, limit - reserved.length));
  reserved.push(...satellites);
  reserved.push(
    ...events.filter(isFirms).slice(0, Math.min(RESERVED_FIRMS, limit - reserved.length)),
  );
  const ids = new Set(reserved.map((event) => event.id));
  const remaining = events.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length);
  return Object.fromEntries([...reserved, ...remaining].map((event) => [event.id, event]));
}
