import { expect, it } from 'vitest';
import type { TerrainElevations } from '@/lib/api/terrain';
import { createRfTerrainRadials } from './rfTerrainSampling';
import { mergeRfTerrainSamples } from './rfTerrainMerge';

function batch(radiusKm: number) {
  const plan = createRfTerrainRadials([0, 51], radiusKm);
  const elevations: TerrainElevations = {
    elevations_m: plan.positions.map(() => 0),
    zoom: 10,
    resolution_m: 100,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Test credits',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: 'Test terrain',
  };
  return { plan, elevations };
}

it('retains both completed grids in sorted bounded profiles without claiming finer DEM resolution', () => {
  const first = batch(5),
    second = batch(10);
  second.elevations.resolution_m = 80;
  first.elevations.elevations_m[3] = 500;
  const merged = mergeRfTerrainSamples(first, second);
  expect(merged.plan.maxDistanceKm).toBe(10);
  expect(merged.plan.positions).toHaveLength(817);
  expect(merged.elevations.elevations_m).toHaveLength(817);
  expect(merged.elevations.elevations_m).toContain(500);
  expect(merged.elevations.resolution_m).toBe(100);
  expect(
    merged.plan.profiles.every(
      (profile) => profile.indices[0] === 0 && profile.indices.length <= 35,
    ),
  ).toBe(true);
  for (const { distancesM } of merged.plan.profiles) {
    expect(distancesM.at(-1)).toBe(10_000);
    expect(
      distancesM.every((distance, index) => index === 0 || distance > distancesM[index - 1]!),
    ).toBe(true);
  }
});

it('drops only evidence outside a reduced radius and deduplicates repeated sample locations', () => {
  const first = batch(10),
    second = batch(5);
  first.elevations.elevations_m[17] = 900;
  const merged = mergeRfTerrainSamples(first, second);
  expect(merged.plan.maxDistanceKm).toBe(5);
  expect(merged.elevations.elevations_m).not.toContain(900);
  expect(
    merged.plan.profiles.every((profile) =>
      profile.distancesM.every((distance) => distance <= 5000),
    ),
  ).toBe(true);
  expect(mergeRfTerrainSamples(first, first).plan.positions).toHaveLength(409);
});

it('rejects conflicting elevations rather than raising a terrain point that later becomes a receiver', () => {
  const first = batch(5),
    second = batch(5);
  second.elevations.elevations_m[1] = 1;
  expect(() => mergeRfTerrainSamples(first, second)).toThrow(/repeated sample elevation/);
  second.elevations.elevations_m[0] = 1;
  expect(() => mergeRfTerrainSamples(first, second)).toThrow(/transmitter elevation/);
});

it('rejects incompatible or incomplete source geometry', () => {
  const first = batch(5),
    second = batch(10);
  second.plan.origin = [1, 51];
  expect(() => mergeRfTerrainSamples(first, second)).toThrow(/compatible sampling source/);
  const missing = batch(10);
  missing.elevations.elevations_m.pop();
  expect(() => mergeRfTerrainSamples(first, missing)).toThrow(/compatible sampling source/);
  const bearings = batch(10);
  bearings.plan.profiles[0]!.bearingDegrees = 1;
  expect(() => mergeRfTerrainSamples(first, bearings)).toThrow(/different sampled bearings/);
});

it.each([
  { provider: 'Another provider' },
  { zoom: 11 },
  { attribution_url: 'https://example.test/different-source' },
])('rejects incompatible provider metadata %o before combining evidence', (changed) => {
  const first = batch(5),
    second = batch(10);
  Object.assign(second.elevations, changed);
  expect(() => mergeRfTerrainSamples(first, second)).toThrow(/compatible sampling source/);
});
