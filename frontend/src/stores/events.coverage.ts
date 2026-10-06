import { compareText } from './events.batch';
import { mergeFreshnessHint } from './events.freshness';
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

interface TimedEvent {
  event: LiveEvent;
  observedAt: string;
  publishedAt: string | null;
  times: readonly [number, number];
}

// Reuse the sort record as well as its parsed times across batches. Witness the raw fields
// so a caller correcting an existing object cannot leave the eviction order stale.
const parsedTimes = new WeakMap<LiveEvent, TimedEvent>();
function eventTimes(event: LiveEvent): TimedEvent {
  let keyed = parsedTimes.get(event);
  if (keyed?.observedAt !== event.observed_at || keyed.publishedAt !== event.published_at) {
    keyed = {
      event,
      observedAt: event.observed_at,
      publishedAt: event.published_at,
      times: [Date.parse(event.observed_at), Date.parse(event.published_at ?? event.observed_at)],
    };
    parsedTimes.set(event, keyed);
  }
  return keyed;
}

function remainingEvents(fair: LiveEvent[], reserved: ReadonlySet<string>, room: number) {
  // Preserve the existing slice semantics for unusual caller-supplied numeric limits.
  if (!Number.isSafeInteger(room) || room < 0)
    return fair.filter((event) => !reserved.has(event.id)).slice(0, room);
  const remaining: LiveEvent[] = [];
  for (const event of fair) {
    if (remaining.length >= room) break;
    if (!reserved.has(event.id)) remaining.push(event);
  }
  return remaining;
}

/** Reserve ships and satellites, favouring specific public catalogues over bulk active data. */
export function boundedEvents(
  byId: Record<string, LiveEvent>,
  limit: number,
  selectedId?: string | null,
  previous?: readonly LiveEvent[],
): Record<string, LiveEvent> {
  const events = Object.values(byId);
  if (events.length <= limit) return byId;
  // Look each record up once per rebuild, not at every comparison.
  const keyed = events.map(eventTimes);
  const hinted = previous ? mergeFreshnessHint(byId, keyed, previous) : null;
  if (hinted === null) {
    keyed.sort(
      (a, b) =>
        b.times[0] - a.times[0] || b.times[1] - a.times[1] || compareText(a.event.id, b.event.id),
    );
  }
  const fair = geographicOrder((hinted ?? keyed).map((item) => item.event));
  const militaryVessels: LiveEvent[] = [];
  const vessels: LiveEvent[] = [];
  const militaryAircraft: LiveEvent[] = [];
  const aircraft: LiveEvent[] = [];
  const satellites: LiveEvent[] = [];
  const fires: LiveEvent[] = [];
  // These category-owned buckets are disjoint. Partition current military priority once,
  // retaining fair order within each priority exactly as the former stable sorts did.
  for (const event of fair) {
    if (event.category === 'maritime' && event.subtype === 'vessel_position')
      (isMilitaryVessel(event) ? militaryVessels : vessels).push(event);
    else if (event.category === 'aviation')
      (isMilitaryAircraft(event) ? militaryAircraft : aircraft).push(event);
    else if (isSatellite(event)) satellites.push(event);
    else if (isFirms(event)) fires.push(event);
  }
  const reserved = [...militaryVessels, ...vessels].slice(0, Math.min(RESERVED_VESSELS, limit));
  reserved.push(
    ...[...militaryAircraft, ...aircraft].slice(
      0,
      Math.min(RESERVED_AIRCRAFT, limit - reserved.length),
    ),
  );
  reserved.push(
    ...satellites
      .sort((a, b) => satellitePriority(b) - satellitePriority(a))
      .slice(0, Math.min(RESERVED_SATELLITES, limit - reserved.length)),
  );
  reserved.push(...fires.slice(0, Math.min(RESERVED_FIRMS, limit - reserved.length)));
  const ids = new Set(reserved.map((event) => event.id));
  const remaining = remainingEvents(fair, ids, limit - reserved.length);
  const retained = [...reserved, ...remaining];
  const selected = selectedId ? byId[selectedId] : undefined;
  if (selected && retained.length > 0 && !retained.some((event) => event.id === selected.id))
    retained[retained.length - 1] = selected;
  return Object.fromEntries(retained.map((event) => [event.id, event]));
}
