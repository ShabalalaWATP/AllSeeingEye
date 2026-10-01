import { compareText } from './events.batch';
import { geographicOrder } from './events.geography';
import { compareEventFreshness as observationOrder } from '@/lib/liveEventSnapshot';
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

/** Keep the newer copy when a vessel appears in both asynchronous snapshots. */
export function mergeSnapshots(main: LiveEvent[], maritime: LiveEvent[]): Map<string, LiveEvent> {
  const merged = new Map(main.map((event) => [event.id, event]));
  for (const event of maritime) {
    const previous = merged.get(event.id);
    if (!previous || observationOrder(event, previous) >= 0) merged.set(event.id, event);
  }
  return merged;
}

// Records are immutable, so each one's timestamps are parsed once across stream batches,
// not at every comparison or every rebuild of a full sensor mirror.
const parsedTimes = new WeakMap<LiveEvent, readonly [number, number]>();
function eventTimes(event: LiveEvent): readonly [number, number] {
  let times = parsedTimes.get(event);
  if (times === undefined) {
    times = [Date.parse(event.observed_at), Date.parse(event.published_at ?? event.observed_at)];
    parsedTimes.set(event, times);
  }
  return times;
}

/** Reserve ships and satellites, favouring specific public catalogues over bulk active data. */
export function boundedEvents(
  byId: Record<string, LiveEvent>,
  limit: number,
  selectedId?: string | null,
): Record<string, LiveEvent> {
  const events = Object.values(byId);
  if (events.length <= limit) return byId;
  // Look each record's times up once per rebuild, not at every comparison.
  const keyed = events.map((event) => ({ event, times: eventTimes(event) }));
  keyed.sort(
    (a, b) =>
      b.times[0] - a.times[0] || b.times[1] - a.times[1] || compareText(a.event.id, b.event.id),
  );
  const fair = geographicOrder(keyed.map((item) => item.event));
  const reserved = fair
    .filter((event) => event.category === 'maritime' && event.subtype === 'vessel_position')
    .sort((a, b) => Number(isMilitaryVessel(b)) - Number(isMilitaryVessel(a)))
    .slice(0, Math.min(RESERVED_VESSELS, limit));
  reserved.push(
    ...fair
      .filter((event) => event.category === 'aviation')
      .sort((a, b) => Number(isMilitaryAircraft(b)) - Number(isMilitaryAircraft(a)))
      .slice(0, Math.min(RESERVED_AIRCRAFT, limit - reserved.length)),
  );
  const satellites = fair
    .filter(isSatellite)
    .sort((a, b) => satellitePriority(b) - satellitePriority(a))
    .slice(0, Math.min(RESERVED_SATELLITES, limit - reserved.length));
  reserved.push(...satellites);
  reserved.push(
    ...fair.filter(isFirms).slice(0, Math.min(RESERVED_FIRMS, limit - reserved.length)),
  );
  const ids = new Set(reserved.map((event) => event.id));
  const remaining = fair.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length);
  const retained = [...reserved, ...remaining];
  const selected = selectedId ? byId[selectedId] : undefined;
  if (selected && retained.length > 0 && !retained.some((event) => event.id === selected.id))
    retained[retained.length - 1] = selected;
  return Object.fromEntries(retained.map((event) => [event.id, event]));
}
