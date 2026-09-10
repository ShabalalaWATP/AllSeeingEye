import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import {
  createRfTerrainPath,
  createRfTerrainRadials,
  RF_TERRAIN_MAX_PATH_SAMPLES,
  RF_TERRAIN_MAX_SAMPLES,
} from './rfTerrainSampling';

const origin: Position = [0, 0];
const powerful = {
  ...DEFAULT_RF_INPUTS,
  transmitHeightM: 100,
  receiveHeightM: 100,
  transmitDbm: 40,
  sensitivityDbm: -120,
};
function destination(start: Position, bearing: number, distanceM: number): Position {
  const point = Geodesic.WGS84.Direct(start[1], start[0], bearing, distanceM);
  return [point.lon2!, point.lat2!];
}

it('screens a nearby ridge that a linear 50 km radial plan skipped', () => {
  const plan = createRfTerrainRadials(origin, 50);
  const ridge = (distanceM: number) => (distanceM >= 150 && distanceM <= 200 ? 500 : 0);
  const elevations = plan.positions.map((position) =>
    ridge(Geodesic.WGS84.Inverse(0, 0, position[1], position[0]).s12!),
  );
  const analysis = analyseRfTerrain(powerful, plan, elevations);
  expect(plan.positions).toHaveLength(RF_TERRAIN_MAX_SAMPLES);
  expect(analysis.radials[0]?.status).toBe('blocked');
  expect(analysis.radials[0]?.clearDistanceKm).toBe(0);
  expect(analysis.radials[0]?.stopDistanceKm).toBeCloseTo(50 * (2 / 17) ** 2, 9);
  expect(analysis.radials[0]?.stopDistanceKm).toBeLessThan(0.7);

  // Previous evenly spaced locations all missed this same synthetic ridge.
  const linearDistances = Array.from({ length: 18 }, (_, index) => (50_000 * index) / 17);
  const linear = evaluateRfTerrainProfile(
    powerful,
    linearDistances.map((distance) => destination(origin, 0, distance)),
    linearDistances,
    linearDistances.map(ridge),
  );
  expect(linear.status).toBe('clear');
});

it('resolves a narrow path ridge missed by the former 129-point allocation', () => {
  const receiver = destination(origin, 90, 20_000);
  const improved = createRfTerrainPath(origin, receiver);
  const old = createRfTerrainPath(origin, receiver, 129);
  const ridge = (distanceM: number) => (distanceM >= 350 && distanceM <= 450 ? 500 : 0);
  const result = (plan: ReturnType<typeof createRfTerrainPath>) =>
    analyseRfTerrain(powerful, plan, plan.profiles[0]!.distancesM.map(ridge));
  expect(result(old).path?.status).toBe('clear');
  expect(result(improved).path?.status).toBe('blocked');
  expect(improved.profiles[0]!.distancesM[1]).toBeLessThanOrEqual(100);
});

it('caps long paths at 769 aligned points while retaining the exact receiver', () => {
  const receiver = destination(origin, 35, 199_000);
  const plan = createRfTerrainPath(origin, receiver);
  expect(plan.positions).toHaveLength(RF_TERRAIN_MAX_PATH_SAMPLES);
  expect(plan.positions.at(-1)).toEqual(receiver);
  const distances = plan.profiles[0]!.distancesM;
  expect(distances).toHaveLength(plan.positions.length);
  expect(distances.at(-1)).toBeCloseTo(199_000, 6);
  expect(distances[1]).toBeLessThan(260);
  expect(
    distances.every((distance, index) => index === 0 || distance > distances[index - 1]!),
  ).toBe(true);
  expect(
    analyseRfTerrain(
      powerful,
      plan,
      plan.positions.map(() => 0),
    ).sampleCount,
  ).toBe(769);
});

it('supports metre-scale paths and rejects invalid explicit sample counts', () => {
  const receiver = destination(origin, 90, 1.5);
  const plan = createRfTerrainPath(origin, receiver);
  expect(plan.positions).toHaveLength(3);
  expect(plan.profiles[0]!.distancesM[1]).toBeCloseTo(0.75, 7);
  expect(createRfTerrainPath(origin, destination(origin, 90, 500), 769).positions).toHaveLength(
    769,
  );
  for (const samples of [2, 770, 3.5, NaN, Infinity]) {
    expect(() => createRfTerrainPath(origin, receiver, samples)).toThrow(/Path samples/);
  }
  expect(() => createRfTerrainPath(origin, destination(origin, 90, 0.5))).toThrow(/1 metre/);
});

it('keeps tiny radial profiles monotonic and their first assessed target at least one metre away', () => {
  for (const steps of [2, 4, 17]) {
    const plan = createRfTerrainRadials(origin, 0.01, 4, steps);
    const distances = plan.profiles[0]!.distancesM;
    expect(distances[2]).toBeGreaterThanOrEqual(1);
    expect(distances.at(-1)).toBe(10);
    expect(
      distances.every((distance, index) => index === 0 || distance > distances[index - 1]!),
    ).toBe(true);
    expect(
      analyseRfTerrain(
        powerful,
        plan,
        plan.positions.map(() => 0),
      ).radials,
    ).toHaveLength(4);
  }
});

it('retains dateline wrapping, tile admission and the 64 KiB request limit', () => {
  const dateline = createRfTerrainPath([179.5, 0], [-179.5, 0]);
  expect(dateline.positions).toHaveLength(769);
  expect(dateline.positions.every(([lon]) => lon >= -180 && lon <= 180)).toBe(true);
  for (const start of [
    origin,
    [-120.123456789, -45.987654321] as Position,
    [179.5, 0] as Position,
  ]) {
    const plan = createRfTerrainPath(start, destination(start, 70, 199_000));
    const body = JSON.stringify({ positions: plan.positions.map(([lon, lat]) => ({ lon, lat })) });
    expect(new TextEncoder().encode(body).byteLength).toBeLessThan(64 * 1024);
  }
  expect(() => createRfTerrainRadials([0, 84], 50)).toThrow(/64 tiles/);
  expect(() => createRfTerrainPath([0, 86], [0, 85])).toThrow(/latitude/);
});
