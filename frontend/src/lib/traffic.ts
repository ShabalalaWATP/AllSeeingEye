import type { LiveEvent } from './api/eventSchemas';

export const MILITARY_AIRCRAFT_COLOUR = [255, 196, 87, 255] as const;
export const MILITARY_VESSEL_COLOUR = [231, 141, 255, 255] as const;

/** Classification must be present in provider data, never inferred from a name or callsign. */
export function isMilitaryAircraft(event: LiveEvent): boolean {
  return (
    event.category === 'aviation' &&
    (event.subtype === 'military_aircraft' ||
      event.tags.includes('military') ||
      event.attributes.military === true)
  );
}

export function isMilitaryVessel(event: LiveEvent): boolean {
  return (
    event.category === 'maritime' &&
    event.subtype === 'vessel_position' &&
    (event.attributes.military === true ||
      event.tags.includes('military') ||
      event.attributes.ship_type_code === 35)
  );
}

export function militaryTrafficLabel(event: LiveEvent): string | null {
  if (isMilitaryAircraft(event)) return 'Provider-labelled military aircraft';
  if (isMilitaryVessel(event)) return 'Reported military operations';
  return null;
}

export function trafficSearchText(event: LiveEvent): string {
  const fields = [
    'callsign',
    'registration',
    'icao24',
    'icao_hex',
    'hex',
    'mmsi',
    'imo',
    'ship_name',
    'name',
  ];
  return [
    event.title,
    event.id,
    event.source_id,
    ...fields.map((key) => event.attributes[key] ?? ''),
  ]
    .join(' ')
    .toLowerCase();
}
