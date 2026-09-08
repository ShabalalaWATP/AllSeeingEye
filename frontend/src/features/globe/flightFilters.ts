import type { LiveEvent } from '@/lib/api/eventSchemas';

export type FlightFilter = 'all' | 'military';

/** Only explicit provider classification qualifies, never callsign or aircraft shape. */
export function isMilitaryFlight(event: LiveEvent): boolean {
  return (
    event.category === 'aviation' &&
    (event.subtype === 'military_aircraft' || event.tags.includes('military'))
  );
}

export function matchesFlightFilter(event: LiveEvent, filter: FlightFilter): boolean {
  return filter === 'all' || event.category !== 'aviation' || isMilitaryFlight(event);
}
