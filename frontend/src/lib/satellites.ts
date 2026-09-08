import type { LiveEvent } from '@/lib/api/eventSchemas';

export const MAX_SATELLITE_POSITION_AGE_MS = 10 * 60_000;

export function isCurrentSatellitePosition(event: LiveEvent, now: number): boolean {
  const value = event.attributes.position_at ?? event.published_at;
  const timestamp = typeof value === 'string' ? Date.parse(value) : NaN;
  return (
    Number.isFinite(timestamp) &&
    timestamp >= now - MAX_SATELLITE_POSITION_AGE_MS &&
    timestamp <= now + 60_000
  );
}

export type SatelliteGroup = 'all' | 'crewed' | 'military' | 'skynet';

export function isSatellite(event: LiveEvent): boolean {
  return event.category === 'space' && event.subtype === 'satellite';
}

/** Prefer the more specific public catalogue when several feeds describe one object. */
export function satellitePriority(event: LiveEvent): number {
  if (event.source_id === 'celestrak_skynet') return 3;
  if (event.source_id === 'celestrak_military') return 2;
  if (event.source_id === 'celestrak_stations') return 1;
  return 0;
}

export function matchesSatelliteGroup(event: LiveEvent, group: SatelliteGroup): boolean {
  if (group === 'all') return true;
  if (group === 'crewed') return event.source_id === 'celestrak_stations';
  if (group === 'skynet') return event.tags.includes('skynet');
  return event.attributes.military_public_catalogue === true;
}

/** Keep all other layers intact; one marker per NORAD object for the satellite layer. */
export function filterSatellites(
  events: LiveEvent[],
  group: SatelliteGroup,
  now?: number,
): LiveEvent[] {
  const result: LiveEvent[] = [];
  const satellites = new Map<string, LiveEvent>();
  for (const event of events) {
    if (!isSatellite(event)) {
      result.push(event);
      continue;
    }
    if (
      !matchesSatelliteGroup(event, group) ||
      (now !== undefined && !isCurrentSatellitePosition(event, now))
    )
      continue;
    const norad = event.attributes.norad_id;
    const key = typeof norad === 'string' || typeof norad === 'number' ? String(norad) : event.id;
    const previous = satellites.get(key);
    if (
      !previous ||
      satellitePriority(event) > satellitePriority(previous) ||
      (satellitePriority(event) === satellitePriority(previous) &&
        Date.parse(event.observed_at) > Date.parse(previous.observed_at))
    )
      satellites.set(key, event);
  }
  return [...result, ...satellites.values()];
}
