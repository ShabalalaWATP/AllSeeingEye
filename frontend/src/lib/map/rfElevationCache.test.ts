import { expect, it } from 'vitest';
import { RfElevationCache, RF_TERRAIN_CACHE_TTL_MS } from './rfElevationCache';
import type { TerrainElevations } from '@/lib/api/terrain';
import type { Position } from './geoJsonTypes';

const first: Position[] = [
  [0, 0],
  [0.01, 0],
  [0.02, 0],
];
const second: Position[] = [
  [0, 1],
  [0.01, 1],
  [0.02, 1],
];
const third: Position[] = [
  [0, 2],
  [0.01, 2],
  [0.02, 2],
];
const response: TerrainElevations = {
  elevations_m: [1, 2, 3],
  zoom: 10,
  resolution_m: 100,
  provider: 'Mapzen Terrain Tiles',
  attribution: 'Test credits',
  attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
  limitations: 'Test terrain',
};

it('reuses only an exact ordered geometry and retains original evidence metadata', () => {
  const cache = new RfElevationCache();
  cache.put(first, response);
  expect(cache.get(first.map(([lon, lat]) => [lon, lat]))).toEqual(response);
  expect(cache.get([...first].reverse())).toBeNull();
  expect(cache.get(second)).toBeNull();
});

it('bounds storage to two complete batches and evicts the least recently used one', () => {
  const cache = new RfElevationCache();
  cache.put(first, response);
  cache.put(second, response);
  expect(cache.get(first)).toEqual(response);
  cache.put(third, response);
  expect(cache.get(second)).toBeNull();
  expect(cache.get(first)).toEqual(response);
  expect(cache.get(third)).toEqual(response);
  cache.clear();
  expect(cache.get(first)).toBeNull();
  expect(cache.get(third)).toBeNull();
});

it('expires five minutes after receipt, even when the same terrain is repeatedly reused', () => {
  let time = 0;
  const cache = new RfElevationCache(() => time);
  cache.put(first, response);
  time = RF_TERRAIN_CACHE_TTL_MS - 1;
  expect(cache.get(first)).toEqual(response);
  time++;
  expect(cache.get(first)).toBeNull();
  cache.put(first, response);
  expect(cache.get(first)).toEqual(response);
});

it('does not retain partial, non-finite or unbounded batches', () => {
  const cache = new RfElevationCache();
  for (const elevations_m of [[1], [1, NaN, 3], [1, Infinity, 3]]) {
    expect(() => cache.put(first, { ...response, elevations_m })).toThrow(/complete finite/);
  }
  expect(() => cache.put([], { ...response, elevations_m: [] })).toThrow(/complete finite/);
  expect(() => cache.put(Array<Position>(1001).fill([0, 0]), response)).toThrow(/complete finite/);
  expect(cache.get(first)).toBeNull();
});
