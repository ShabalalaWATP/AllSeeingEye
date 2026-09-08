import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';

export type FlightFilter = 'all' | 'military';

/** Only explicit provider classification qualifies, never callsign or aircraft shape. */
export function isMilitaryFlight(event: LiveEvent): boolean {
  return isMilitaryAircraft(event);
}

export function matchesFlightFilter(event: LiveEvent, filter: FlightFilter): boolean {
  return filter === 'all' || event.category !== 'aviation' || isMilitaryFlight(event);
}

export function matchesVesselFilter(event: LiveEvent, filter: FlightFilter): boolean {
  return (
    filter === 'all' ||
    event.category !== 'maritime' ||
    event.subtype !== 'vessel_position' ||
    isMilitaryVessel(event)
  );
}
