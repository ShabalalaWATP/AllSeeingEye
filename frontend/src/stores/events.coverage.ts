import { isSatellite, satellitePriority } from '@/lib/satellites';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';

export const MARITIME_SNAPSHOT_LIMIT = 1_500;
export const RESERVED_VESSELS = 1_500;
export const SATELLITE_SNAPSHOT_LIMIT = 1_500;
export const RESERVED_SATELLITES = 1_000;
export const FIRMS_SNAPSHOT_LIMIT = 1_000;
export const RESERVED_FIRMS = 500;
export const AVIATION_SNAPSHOT_LIMIT = 2_000;
export const RESERVED_AIRCRAFT = 1_500;

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
  selectedId?: string | null,
): Record<string, LiveEvent> {
  const events = Object.values(byId);
  if (events.length <= limit) return byId;
  // Parse each timestamp once, not at every comparison of a full sensor mirror.
  const times = new Map(
    events.map((event) => [
      event,
      [Date.parse(event.observed_at), Date.parse(event.published_at ?? event.observed_at)] as const,
    ]),
  );
  const newestFirst = (a: LiveEvent, b: LiveEvent) => {
    const left = times.get(a) ?? [0, 0];
    const right = times.get(b) ?? [0, 0];
    return right[0] - left[0] || right[1] - left[1] || a.id.localeCompare(b.id);
  };
  events.sort(newestFirst);
  const reserved = events
    .filter((event) => event.category === 'maritime' && event.subtype === 'vessel_position')
    .sort((a, b) => Number(isMilitaryVessel(b)) - Number(isMilitaryVessel(a)))
    .slice(0, Math.min(RESERVED_VESSELS, limit));
  reserved.push(
    ...events
      .filter((event) => event.category === 'aviation')
      .sort((a, b) => Number(isMilitaryAircraft(b)) - Number(isMilitaryAircraft(a)))
      .slice(0, Math.min(RESERVED_AIRCRAFT, limit - reserved.length)),
  );
  const satellites = events
    .filter(isSatellite)
    .sort((a, b) => satellitePriority(b) - satellitePriority(a) || newestFirst(a, b))
    .slice(0, Math.min(RESERVED_SATELLITES, limit - reserved.length));
  reserved.push(...satellites);
  reserved.push(
    ...events.filter(isFirms).slice(0, Math.min(RESERVED_FIRMS, limit - reserved.length)),
  );
  const ids = new Set(reserved.map((event) => event.id));
  const remaining = events.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length);
  const retained = [...reserved, ...remaining];
  const selected = selectedId ? byId[selectedId] : undefined;
  if (selected && retained.length > 0 && !retained.some((event) => event.id === selected.id))
    retained[retained.length - 1] = selected;
  return Object.fromEntries(retained.map((event) => [event.id, event]));
}
