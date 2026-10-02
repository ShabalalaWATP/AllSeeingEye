import { describe, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { eventFacts, eventTimeLabel } from './eventFacts';

function facts(overrides: Partial<LiveEvent>) {
  return Object.fromEntries(
    eventFacts(liveEvent(overrides))?.facts.map(({ label, value }) => [label, value]) ?? [],
  );
}

const aircraft = { category: 'aviation', subtype: 'aircraft' } as const;
const vessel = { category: 'maritime', subtype: 'vessel_position' } as const;
const satellite = { category: 'space', subtype: 'satellite' } as const;
const thermal = { category: 'disaster', subtype: 'thermal_detection' } as const;

describe('selected aircraft facts', () => {
  it('retains adapter units, zero movement and a reported ground flag', () => {
    const result = facts({
      ...aircraft,
      attributes: {
        callsign: ' TEST123 ',
        registration: 'G-TEST',
        icao_hex: 'abcdef',
        aircraft_type: 'A320',
        altitude_ft: 0,
        ground_speed_kt: 0,
        track_deg: 0,
        vertical_rate_fpm: -500,
        on_ground: true,
      },
    });
    expect(result).toMatchObject({
      Callsign: 'TEST123',
      Registration: 'G-TEST',
      'ICAO hex': 'abcdef',
      'Barometric altitude': '0 ft',
      'Ground speed': '0 kn',
      'Ground track': '0 °',
      'Vertical rate': '-500 ft/min',
      'Ground indication': 'On ground',
    });
    expect(facts({ ...aircraft, attributes: { on_ground: false } })['Ground indication']).toBe(
      'Not flagged on ground',
    );
  });

  it('does not invent units, military status or values from incomplete fields', () => {
    const result = facts({
      ...aircraft,
      title: 'RAF example',
      attributes: { callsign: 'NAVY123', altitude: 9000, velocity: 123, military: false },
    });
    expect(result['Barometric altitude']).toBe('Not reported');
    expect(result['Ground speed']).toBe('Not reported');
    expect(result['Ground indication']).toBe('Not reported');
    expect(result).not.toHaveProperty('Classification');
    expect(facts({ ...aircraft, attributes: { military: true } }).Classification).toBe(
      'Provider-labelled military aircraft',
    );
  });

  it.each(['ladd_aircraft', 'pia_aircraft', 'emergency', 'military_aircraft'])(
    'supports the existing %s aircraft subtype',
    (subtype) => {
      expect(eventFacts(liveEvent({ ...aircraft, subtype }))?.title).toBe('Aircraft details');
    },
  );
});

describe('selected vessel facts', () => {
  it('preserves leading zero identifiers and reports codes without inventing identities', () => {
    const result = facts({
      ...vessel,
      title: 'HMS Example',
      attributes: {
        mmsi: '000123456',
        imo: 1234567,
        ship_type_label: 'Reported AIS ship type',
        ship_type_code: 70,
        navigation_status_code: 0,
        speed_over_ground_knots: 0,
        heading_deg: 50,
        course_over_ground_deg: 55,
      },
    });
    expect(result).toMatchObject({
      MMSI: '000123456',
      'IMO number': '1234567',
      'AIS ship type code': '70',
      'Reported navigation status': 'Under way using engine (AIS 0)',
      'Speed over ground': '0 kn',
      'True heading': '50 °',
      'Course over ground': '55 °',
    });
    expect(result).not.toHaveProperty('Classification');
  });

  it('keeps unknown heading distinct from course and retains reported military classification', () => {
    const result = facts({
      ...vessel,
      attributes: { ship_type_code: 35, heading_deg: 511, course_over_ground_deg: 270 },
    });
    expect(result['True heading']).toBe('Not reported');
    expect(result['Course over ground']).toBe('270 °');
    expect(result['IMO number']).toBe('Not reported');
    expect(result.Classification).toBe('Reported military operations');
  });
});

describe('satellite observation context', () => {
  it('labels propagation and age at the position time, interpreting GP epochs as UTC', () => {
    const result = facts({
      ...satellite,
      attributes: {
        norad_id: '25544',
        object_id: '1998-067A',
        altitude_km: 400.2,
        speed_km_s: 7.66,
        epoch: '2026-09-01T12:00:00',
        epoch_age_hours: 96,
        position_at: '2026-09-05T12:00:00Z',
        position_kind: 'propagated',
        is_stale: true,
      },
    });
    expect(result).toMatchObject({
      'NORAD catalogue ID': '25544',
      Altitude: '400.2 km',
      'Orbital speed': '7.66 km/s',
      'Orbital element epoch': '1 Sept 2026, 12:00 UTC',
      'Element age at position time': '96 h',
      'Position method': 'SGP4 propagation',
      'Orbital element status': 'Stale elements',
    });
    expect(eventFacts(liveEvent(satellite))?.note).toContain('not a live observation');
  });

  it('does not turn future orbital epochs into fresh observations or parse invalid dates', () => {
    const result = facts({
      ...satellite,
      attributes: { epoch_age_hours: -1.25, epoch: 'bad date', is_stale: false },
    });
    expect(result['Element age at position time']).toBe('1.25 h after position time');
    expect(result['Orbital element epoch']).toBe('Not reported');
    expect(result['Position method']).toBe('Not reported');
    expect(result['Orbital element status']).toBe('Within collection age limit');
  });
});

it('preserves negative earthquake magnitudes and separately labels the reported scale and depth', () => {
  const result = facts({
    category: 'disaster',
    subtype: 'earthquake',
    attributes: { magnitude: -0.7, magnitude_type: 'ml', depth_km: -1, status: 'automatic' },
  });
  expect(result).toEqual({
    Magnitude: '-0.7',
    'Magnitude scale': 'ml',
    Depth: '-1 km',
    'Solution status': 'automatic',
  });
});

describe('FIRMS sensor measurements', () => {
  it('preserves acquisition, confidence, FRP and footprint units with thermal limitations', () => {
    const result = facts({
      ...thermal,
      published_at: '2026-09-05T09:30:00Z',
      attributes: {
        satellite: 'NOAA-20',
        instrument: 'VIIRS',
        sensor_confidence: 'n',
        fire_radiative_power_mw: 8.2,
        nominal_pixel_metres: 375,
        daynight: 'D',
      },
    });
    expect(result).toMatchObject({
      Satellite: 'NOAA-20',
      Instrument: 'VIIRS',
      'Acquisition time': '5 Sept 2026, 09:30 UTC',
      'Sensor confidence': 'Nominal',
      'Fire radiative power': '8.2 MW',
      'Nominal pixel size': '375 m',
      Overpass: 'Day',
    });
    expect(eventFacts(liveEvent(thermal))?.note).toContain('not a confirmed wildfire');
  });

  it.each([
    ['l', 'Low'],
    ['h', 'High'],
    ['constructor', 'Not reported'],
    ['unknown', 'Not reported'],
  ])('only interprets known sensor confidence %s', (input, expected) => {
    expect(
      facts({ ...thermal, attributes: { sensor_confidence: input } })['Sensor confidence'],
    ).toBe(expected);
  });

  it('does not interpret missing or negative FRP as radiative power', () => {
    expect(
      facts({ ...thermal, attributes: { fire_radiative_power_mw: -0.53 } })['Fire radiative power'],
    ).toBe('Not reported');
    expect(
      facts({ ...thermal, attributes: { fire_radiative_power_mw: 0, daynight: 'N' } }),
    ).toMatchObject({ 'Fire radiative power': '0 MW', Overpass: 'Night' });
  });
});

it.each([null, '', false, '123', NaN, Infinity, -Infinity])(
  'rejects missing or non-finite numeric measurements: %s',
  (value) => {
    expect(facts({ ...aircraft, attributes: { altitude_ft: value } })['Barometric altitude']).toBe(
      'Not reported',
    );
  },
);

it('does not apply an object template to unrelated news, launches or maritime reports', () => {
  for (const category of ['news', 'aviation', 'space', 'maritime'] as const)
    expect(eventFacts(liveEvent({ category, subtype: 'news_report' }))).toBeNull();
});

it('gives sensor and position timestamps precise labels', () => {
  expect(eventTimeLabel(liveEvent(vessel))).toBe('Position record time');
  expect(eventTimeLabel(liveEvent(satellite))).toBe('Position update');
  expect(eventTimeLabel(liveEvent(thermal))).toBe('Acquisition time');
  expect(eventTimeLabel(liveEvent())).toBe('Published');
});
