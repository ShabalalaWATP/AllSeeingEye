import { expect, it } from 'vitest';
import { formatDms, fromUtm, parseCoordinate, toUtm } from './coordinateWorkbench';
import { createResearchCorridor } from './terrainCorridor';
import { simplifyCorridorPath } from './terrainCorridorSimplification';
import type { Position } from './geoJsonTypes';

it('formats south/east hemispheres and assigns all Svalbard exception zones', () => {
  expect(formatDms(-33.5, 'latitude')).toBe('33° 30′ 0.00″ S');
  expect(formatDms(151.5, 'longitude')).toBe('151° 30′ 0.00″ E');
  expect(toUtm([5, 78])?.zone).toBe(31);
  expect(toUtm([25, 78])?.zone).toBe(35);
  expect(toUtm([38, 78])?.zone).toBe(37);
  expect(toUtm([0, -81])).toBeNull();
});

it('rejects oversized coordinates and fractional-minute DMS with extra seconds', () => {
  expect(() => parseCoordinate('1'.repeat(101), 'latitude')).toThrow(
    'Coordinate input is too long.',
  );
  expect(() => parseCoordinate('51 30.5 10 N', 'latitude')).toThrow(/only the final component/);
});

it.each([
  { zone: 0, hemisphere: 'N' as const, easting: 500000, northing: 0 },
  { zone: 30.5, hemisphere: 'N' as const, easting: 500000, northing: 0 },
  { zone: 30, hemisphere: 'N' as const, easting: 99999, northing: 0 },
  { zone: 30, hemisphere: 'N' as const, easting: 900001, northing: 0 },
  { zone: 30, hemisphere: 'N' as const, easting: 500000, northing: NaN },
  { zone: 30, hemisphere: 'N' as const, easting: 500000, northing: -1 },
  { zone: 30, hemisphere: 'N' as const, easting: 500000, northing: 10000001 },
])('rejects out-of-domain UTM input %#', (value) => {
  expect(() => fromUtm(value)).toThrow(/Use UTM zone/);
});

it('rejects southern UTM outside its latitude coverage', () => {
  expect(() => fromUtm({ zone: 30, hemisphere: 'S', easting: 500000, northing: 1 })).toThrow(
    /latitude coverage/,
  );
});

it('bounds corridor input sizes and both width limits', () => {
  expect(() => createResearchCorridor([], 1)).toThrow(/2–32/);
  expect(() =>
    createResearchCorridor(
      Array.from({ length: 33 }, (_, i): Position => [i / 1000, 51]),
      1,
    ),
  ).toThrow(/2–32/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [0.01, 51],
      ],
      NaN,
    ),
  ).toThrow(/Distance/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [0.01, 51],
      ],
      21,
    ),
  ).toThrow(/Distance/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 0],
        [0.1, 0],
      ],
      49,
    ),
  ).toThrow(/50 to 5,000/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 0],
        [0.1, 0],
      ],
      5001,
    ),
  ).toThrow(/50 to 5,000/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 0],
        [0.00000001, 0],
      ],
      50,
    ),
  ).toThrow(/1 metre to 200 km/);
});
