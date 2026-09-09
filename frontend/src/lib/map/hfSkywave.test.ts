import { expect, it } from 'vitest';
import { calculateHfSkywave, hfVirtualHop } from './hfSkywave';
import type { HfSkywaveInputs } from './hfSkywave';
import { hfSkywaveLayers } from './hfSkywaveLayers';

const scenario: HfSkywaveInputs = {
  frequencyMHz: 7,
  criticalFrequencyMHz: 5,
  virtualHeightKm: 300,
  minElevationDeg: 5,
  maxElevationDeg: 85,
};

it('matches vertical and tangent spherical-shell geometry at its endpoints', () => {
  const vertical = hfVirtualHop(300, 90);
  expect(vertical.groundDistanceKm).toBe(0);
  expect(vertical.virtualPathKm).toBeCloseTo(600, 8);
  expect(vertical.secantFactor).toBeCloseTo(1, 10);
  const tangent = hfVirtualHop(300, 0);
  expect(tangent.groundDistanceKm).toBeCloseTo(2 * 6371 * Math.acos(6371 / 6671), 8);
  expect(tangent.groundDistanceKm).toBeGreaterThan(3800);
  expect(tangent.groundDistanceKm).toBeLessThan(4000);
  expect(hfVirtualHop(100, 0).groundDistanceKm).toBeGreaterThan(2200);
});

it('forms a bounded single-hop annulus, with nearer hops at higher launch angles', () => {
  const result = calculateHfSkywave(scenario);
  expect(result.compatible).toBe(true);
  expect(result.innerRadiusKm).toBeGreaterThan(0);
  expect(result.outerRadiusKm).toBeGreaterThan(result.innerRadiusKm ?? NaN);
  expect(result.maxElevationDeg).toBeLessThan(scenario.maxElevationDeg);
  expect(hfVirtualHop(300, result.maxElevationDeg).secantFactor * 5).toBeCloseTo(7, 8);
  expect(result.assumptions).toContain('not a coverage footprint');
  const higher = calculateHfSkywave({ ...scenario, minElevationDeg: 20 });
  expect(higher.outerRadiusKm).toBeLessThan(result.outerRadiusKm ?? NaN);
});

it('rejects an incompatible frequency without inventing a range and allows near-vertical low frequency', () => {
  const incompatible = calculateHfSkywave({
    ...scenario,
    frequencyMHz: 30,
    criticalFrequencyMHz: 1,
  });
  expect(incompatible.compatible).toBe(false);
  expect(incompatible.innerRadiusKm).toBeNull();
  expect(incompatible.outerRadiusKm).toBeNull();
  const vertical = calculateHfSkywave({ ...scenario, frequencyMHz: 3, maxElevationDeg: 90 });
  expect(vertical.innerRadiusKm).toBe(0);
  expect(vertical.maxElevationDeg).toBe(90);
});

it.each([
  { frequencyMHz: NaN },
  { frequencyMHz: 1 },
  { frequencyMHz: 31 },
  { criticalFrequencyMHz: 0 },
  { virtualHeightKm: 0 },
  { virtualHeightKm: 1000 },
  { minElevationDeg: -1 },
  { maxElevationDeg: 91 },
  { minElevationDeg: 70, maxElevationDeg: 60 },
])('rejects invalid scenario parameters %j', (input) => {
  expect(() => calculateHfSkywave({ ...scenario, ...input })).toThrow();
});

it('renders two non-interactive outlines and a permanent scenario label at bounded complexity', () => {
  const estimate = {
    origin: [179.8, 0] as [number, number],
    frequencyMHz: 7,
    scenario: calculateHfSkywave(scenario),
  };
  const layers = hfSkywaveLayers(estimate, true);
  expect(layers).toHaveLength(3);
  const paths = layers[0]?.props.data as number[][][];
  expect(paths).toHaveLength(2);
  expect(paths.every((path) => path.length === 73)).toBe(true);
  expect(
    paths.flat().every(([lon, lat]) => Math.abs(lon ?? NaN) <= 180 && Math.abs(lat ?? NaN) <= 90),
  ).toBe(true);
  expect(layers.every((layer) => layer.props.pickable === false)).toBe(true);
  expect(hfSkywaveLayers(null, true)).toEqual([]);
  expect(
    hfSkywaveLayers(
      {
        ...estimate,
        scenario: calculateHfSkywave({ ...scenario, frequencyMHz: 30, criticalFrequencyMHz: 1 }),
      },
      false,
    ),
  ).toEqual([]);
  const polar = hfSkywaveLayers({ ...estimate, origin: [0, 90] }, true);
  expect(polar[1]?.props.data).toEqual([]);
});
