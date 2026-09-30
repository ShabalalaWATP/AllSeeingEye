import { expect, it } from 'vitest';
import { parseRfEngineering, RF_PHYSICAL_REFERENCE, validateRfEngineering } from './rfEngineering';
import { calculateRf, DEFAULT_RF_INPUTS } from './rfPlanning';
import { rfMapEstimate } from './rfMap';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import { rfPathPointStatus } from './rfTerrainPresentation';
import type { Position } from './geoJsonTypes';

const positions: Position[] = [
  [0, 0],
  [0.005, 0],
  [0.01, 0],
];
const distances = [0, 500, 1000];
const settings = { ...RF_PHYSICAL_REFERENCE, reserveDb: 10 };
const input = { ...DEFAULT_RF_INPUTS, distanceKm: 1, transmitHeightM: 30, receiveHeightM: 30 };

it('uses an editable reserve and rejects blank, nonfinite and out-of-bounds assumptions', () => {
  expect(parseRfEngineering()).toEqual(settings);
  expect(parseRfEngineering({ reserveDb: '0' }).reserveDb).toBe(0);
  for (const value of ['', ' ', 'NaN', 'Infinity', '-1', '61'])
    expect(() => parseRfEngineering({ reserveDb: value })).toThrow(/Planning reserve/);
  expect(() => validateRfEngineering({ ...settings, obstacleHeightM: 101 })).toThrow(/obstacle/);
  expect(() => validateRfEngineering({ ...settings, earthFactor: 0 })).toThrow(/Earth factor/);
  expect(parseRfEngineering({ obstacleHeightM: '' }, 'free-space').obstacleHeightM).toBe(0);
  expect(parseRfEngineering({ earthFactor: '', obstacleHeightM: '' }, 'hf-groundwave')).toEqual(
    settings,
  );
});

it('reduces the ideal boundary without misrepresenting reserve as a physical power loss', () => {
  const base = calculateRf(input);
  const planned = calculateRf(input, settings);
  expect(planned.receivedDbm).toBe(base.receivedDbm);
  expect(planned.marginDb).toBe(base.marginDb);
  expect(planned.planningMarginDb).toBe(base.marginDb - 10);
  expect(planned.sensitivityDistanceKm / base.sensitivityDistanceKm).toBeCloseTo(10 ** -0.5, 10);
  const atBoundary = calculateRf({ ...input, distanceKm: planned.sensitivityDistanceKm }, settings);
  expect(atBoundary.planningMarginDb).toBeCloseTo(0, 8);
  const weak = { ...input, transmitDbm: 0 };
  expect(rfMapEstimate(weak, [0, 0], null, settings).radiusKm).toBeLessThan(
    rfMapEstimate(weak, [0, 0]).radiusKm,
  );
});

it('marks a geometrically clear link with insufficient spare margin as risk everywhere', () => {
  const free = calculateRf(input);
  const marginal = { ...input, sensitivityDbm: free.receivedDbm - 5 };
  const physical = evaluateRfTerrainProfile(marginal, positions, distances, [0, 0, 0]);
  const planned = evaluateRfTerrainProfile(marginal, positions, distances, [0, 0, 0], settings);
  expect(physical.status).toBe('clear');
  expect(planned.status).toBe('risk');
  expect(planned.receivedDbm).toBe(physical.receivedDbm);
  expect(planned.marginDb).toBeCloseTo(5, 6);
  expect(planned.planningMarginDb).toBeCloseTo(-5, 6);
  expect(planned.points.map((point) => rfPathPointStatus(planned, point))).toEqual([
    'risk',
    'risk',
    'risk',
  ]);
});

it('adds a stated intermediate obstacle screen without changing ground or site mast elevations', () => {
  const bare = evaluateRfTerrainProfile(input, positions, distances, [100, 100, 100]);
  const screened = evaluateRfTerrainProfile(input, positions, distances, [100, 100, 100], {
    ...settings,
    obstacleHeightM: 40,
  });
  expect(screened.status).toBe('blocked');
  expect(screened.points.map((point) => point.elevationM)).toEqual([100, 100, 100]);
  expect(screened.points.map((point) => point.obstacleHeightM)).toEqual([0, 40, 0]);
  expect(screened.points.map((point) => point.rayHeightM)).toEqual(
    bare.points.map((point) => point.rayHeightM),
  );
  expect(screened.minimumLosClearanceM).toBeCloseTo(bare.minimumLosClearanceM! - 40, 8);
  expect(screened.receivedDbm).toBeLessThan(bare.receivedDbm!);
});

it('applies the selected Earth factor consistently to horizon and terrain curvature', () => {
  const smallerEarth = { ...settings, earthFactor: 1 };
  const a = calculateRf(input, settings),
    b = calculateRf(input, smallerEarth);
  expect(b.horizonKm / a.horizonKm).toBeCloseTo(Math.sqrt(3 / 4), 8);
  expect(b.freeSpaceLossDb).toBe(a.freeSpaceLossDb);
  const terrain = evaluateRfTerrainProfile(input, positions, distances, [0, 0, 0], smallerEarth);
  expect(terrain.points[1]!.earthBulgeM).toBeCloseTo((500 * 500) / (2 * 6371000), 10);
  const unknown = evaluateRfTerrainProfile(input, positions, distances, [0, null, 0], settings);
  expect(unknown.status).toBe('unknown');
  expect(unknown.planningMarginDb).toBeNull();
});
