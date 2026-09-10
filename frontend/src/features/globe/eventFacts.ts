import type { LiveEvent } from '@/lib/api/eventSchemas';
import { formatUtc } from '@/lib/format';
import { militaryTrafficLabel } from '@/lib/traffic';

export interface EventFact {
  label: string;
  value: string;
}

export interface EventFactGroup {
  title: string;
  facts: EventFact[];
  note: string;
}

type Attributes = LiveEvent['attributes'];
const NOT_REPORTED = 'Not reported';
const numberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

// USCG AIS Class A reports, https://www.navcen.uscg.gov/ais-class-a-reports.
// Retain the source code alongside its meaning, including reserved/default codes.
const AIS_NAVIGATION = [
  'Under way using engine',
  'At anchor',
  'Not under command',
  'Restricted manoeuvrability',
  'Constrained by draught',
  'Moored',
  'Aground',
  'Fishing',
  'Under way sailing',
  'Reserved status',
  'Reserved status',
  'Towing astern (regional)',
  'Pushing or towing alongside (regional)',
  'Reserved status',
  'Safety beacon indication',
  'Undefined or test status',
] as const;

function navigationStatus(value: unknown): string {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 15
    ? `${AIS_NAVIGATION[value]} (AIS ${value})`
    : NOT_REPORTED;
}

function text(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value.trim() : NOT_REPORTED;
}

function numeric(value: unknown, unit = '', minimum = -Infinity): string {
  return typeof value === 'number' && Number.isFinite(value) && value >= minimum
    ? `${numberFormat.format(value)}${unit ? ` ${unit}` : ''}`
    : NOT_REPORTED;
}

function identifier(value: unknown): string {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
    ? String(value)
    : text(value);
}

function timestamp(value: unknown, epoch = false): string {
  if (typeof value !== 'string' || !value.trim()) return NOT_REPORTED;
  // CelesTrak GP epochs are UTC, including values without a timezone suffix.
  const iso = epoch && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? `${value}Z` : value;
  return Number.isFinite(Date.parse(iso)) ? formatUtc(iso) : NOT_REPORTED;
}

function fact(label: string, value: string): EventFact {
  return { label, value };
}

function bearing(value: unknown): string {
  return typeof value === 'number' && value < 360 ? numeric(value, '°', 0) : NOT_REPORTED;
}

function aircraftFacts(event: LiveEvent): EventFactGroup {
  const a = event.attributes;
  const classification = militaryTrafficLabel(event);
  return {
    title: 'Aircraft details',
    facts: [
      fact('Callsign', text(a.callsign)),
      fact('Registration', text(a.registration)),
      fact('ICAO hex', text(a.icao_hex)),
      fact('Aircraft type', text(a.aircraft_type)),
      fact('Barometric altitude', numeric(a.altitude_ft, 'ft')),
      fact('Ground speed', numeric(a.ground_speed_kt, 'kn', 0)),
      fact('Ground track', bearing(a.track_deg)),
      fact('Vertical rate', numeric(a.vertical_rate_fpm, 'ft/min')),
      fact(
        'Ground indication',
        a.on_ground === true
          ? 'On ground'
          : a.on_ground === false
            ? 'Not flagged on ground'
            : NOT_REPORTED,
      ),
      ...(classification ? [fact('Classification', classification)] : []),
    ],
    note: 'Transponder reports can be incomplete or incorrect. Ground track is the direction of travel, not the direction the aircraft nose points.',
  };
}

function vesselFacts(event: LiveEvent): EventFactGroup {
  const a = event.attributes;
  const classification = militaryTrafficLabel(event);
  return {
    title: 'Vessel details',
    facts: [
      fact('MMSI', identifier(a.mmsi)),
      fact('IMO number', identifier(a.imo)),
      fact('Reported vessel type', text(a.ship_type_label)),
      fact('AIS ship type code', numeric(a.ship_type_code, '', 0)),
      fact('Reported navigation status', navigationStatus(a.navigation_status_code)),
      fact('Speed over ground', numeric(a.speed_over_ground_knots, 'kn', 0)),
      fact('True heading', bearing(a.heading_deg)),
      fact('Course over ground', bearing(a.course_over_ground_deg)),
      ...(classification ? [fact('Classification', classification)] : []),
    ],
    note: 'AIS identity, ship type and movement are reported assertions, not verified identity or intent. A missing heading is not replaced by course over ground.',
  };
}

function satelliteFacts(a: Attributes): EventFactGroup {
  const age = a.epoch_age_hours;
  return {
    title: 'Satellite details',
    facts: [
      fact('NORAD catalogue ID', identifier(a.norad_id)),
      fact('International designator', text(a.object_id)),
      fact('Altitude', numeric(a.altitude_km, 'km', 0)),
      fact('Orbital speed', numeric(a.speed_km_s, 'km/s', 0)),
      fact('Orbital element epoch', timestamp(a.epoch, true)),
      fact(
        'Element age at position time',
        typeof age === 'number' && Number.isFinite(age) && age < 0
          ? `${numberFormat.format(-age)} h after position time`
          : numeric(age, 'h', 0),
      ),
      fact('Position calculated for', timestamp(a.position_at)),
      fact('Position method', a.position_kind === 'propagated' ? 'SGP4 propagation' : NOT_REPORTED),
      fact(
        'Orbital element status',
        a.is_stale === true
          ? 'Stale elements'
          : a.is_stale === false
            ? 'Within collection age limit'
            : NOT_REPORTED,
      ),
    ],
    note: 'A propagated position is a model estimate from orbital elements, not a live observation. Element age refers to the stated position time, not the time you opened this panel.',
  };
}

function earthquakeFacts(a: Attributes): EventFactGroup {
  return {
    title: 'Earthquake details',
    facts: [
      fact('Magnitude', numeric(a.magnitude)),
      fact('Magnitude scale', text(a.magnitude_type)),
      fact('Depth', numeric(a.depth_km, 'km')),
      fact('Solution status', text(a.status)),
    ],
    note: 'Magnitude and depth are the reported seismic solution. An automatic solution can be revised; magnitude is not a measure of damage at this location.',
  };
}

function fireFacts(event: LiveEvent): EventFactGroup {
  const a = event.attributes;
  const confidence = { l: 'Low', n: 'Nominal', h: 'High' };
  return {
    title: 'Thermal detection details',
    facts: [
      fact('Satellite', text(a.satellite)),
      fact('Instrument', text(a.instrument)),
      fact('Acquisition time', timestamp(event.published_at)),
      fact(
        'Sensor confidence',
        typeof a.sensor_confidence === 'string' && Object.hasOwn(confidence, a.sensor_confidence)
          ? confidence[a.sensor_confidence as keyof typeof confidence]
          : NOT_REPORTED,
      ),
      fact('Fire radiative power', numeric(a.fire_radiative_power_mw, 'MW', 0)),
      fact('Nominal pixel size', numeric(a.nominal_pixel_metres, 'm', 0)),
      fact('Overpass', a.daynight === 'D' ? 'Day' : a.daynight === 'N' ? 'Night' : NOT_REPORTED),
    ],
    note: 'Sensor confidence concerns this thermal detection, not source reliability. A hotspot is not a confirmed wildfire or fire boundary. Radiative power is not burned area.',
  };
}

/** Read only the units and fields retained by the existing feed adapters. */
export function eventFacts(event: LiveEvent): EventFactGroup | null {
  if (
    event.category === 'aviation' &&
    ['aircraft', 'military_aircraft', 'ladd_aircraft', 'pia_aircraft', 'emergency'].includes(
      event.subtype,
    )
  )
    return aircraftFacts(event);
  if (event.category === 'maritime' && event.subtype === 'vessel_position')
    return vesselFacts(event);
  if (event.category === 'space' && event.subtype === 'satellite')
    return satelliteFacts(event.attributes);
  if (event.category === 'disaster' && event.subtype === 'earthquake')
    return earthquakeFacts(event.attributes);
  if (event.category === 'disaster' && event.subtype === 'thermal_detection')
    return fireFacts(event);
  return null;
}

export function eventTimeLabel(event: LiveEvent): string {
  if (event.subtype === 'vessel_position') return 'Position record time';
  if (event.subtype === 'satellite') return 'Position update';
  if (event.subtype === 'thermal_detection') return 'Acquisition time';
  return 'Published';
}
