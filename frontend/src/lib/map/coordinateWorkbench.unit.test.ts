import { describe, expect, it } from 'vitest';
import {
  formatDms,
  fromUtm,
  parseCoordinate,
  parseCoordinatePair,
  toUtm,
} from './coordinateWorkbench';

describe('WGS84 coordinate workbench', () => {
  it('keeps the displayed latitude/longitude order separate from GeoJSON positions', () => {
    expect(parseCoordinatePair('51 30 0 N', '0° 7′ 12″ W')).toEqual([-0.12, 51.5]);
    expect(parseCoordinatePair('-33.9', '151.2')).toEqual([151.2, -33.9]);
    expect(parseCoordinate('51.5N', 'latitude')).toBe(51.5);
    expect(formatDms(51.99999999, 'latitude')).toBe('52° 0′ 0.00″ N');
  });
  it.each([
    ['91', 'latitude'],
    ['181', 'longitude'],
    ['', 'latitude'],
    ['NaN', 'longitude'],
    ['51 60 0 N', 'latitude'],
    ['51 20 60 N', 'latitude'],
    ['51.5 30 N', 'latitude'],
    ['-51N', 'latitude'],
    ['51 E', 'latitude'],
    ['0 N', 'longitude'],
    ['1e2', 'longitude'],
  ] as const)('rejects invalid or ambiguous coordinate %s for %s', (text, axis) => {
    expect(() => parseCoordinate(text, axis)).toThrow();
  });
  it('converts a known equatorial UTM position and southern round trips', () => {
    const equator = toUtm([3, 0])!;
    expect(equator.zone).toBe(31);
    expect(equator.easting).toBeCloseTo(500000, 4);
    expect(equator.northing).toBeCloseTo(0, 4);
    const sydney = toUtm([151.2, -33.9])!;
    expect(sydney.hemisphere).toBe('S');
    const roundTrip = fromUtm(sydney);
    expect(roundTrip[0]).toBeCloseTo(151.2, 6);
    expect(roundTrip[1]).toBeCloseTo(-33.9, 6);
  });
  it('handles Norway, Svalbard and the final UTM zone without extending polar coverage', () => {
    expect(toUtm([4, 60])?.zone).toBe(32);
    expect(toUtm([10, 78])?.zone).toBe(33);
    expect(toUtm([180, 0])?.zone).toBe(60);
    expect(toUtm([0, 85])).toBeNull();
    expect(() => fromUtm({ zone: 61, hemisphere: 'N', easting: 500000, northing: 0 })).toThrow();
    expect(() => fromUtm({ zone: 31, hemisphere: 'N', easting: NaN, northing: 0 })).toThrow();
    expect(() =>
      fromUtm({ zone: 31, hemisphere: 'N', easting: 500000, northing: 9999999 }),
    ).toThrow(/coverage/);
  });
});
