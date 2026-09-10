import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { rfMapEstimate, rfRangeRing } from './rfMap';
import {
  rfReferenceBubble,
  rfReferenceDistance,
  rfReferenceLink,
  rfReferencePaths,
  rfReferencePoint,
} from './rfReferenceGeometry';
import type { Position } from './geoJsonTypes';

it('leaves an absent, coincident or in-range receiver free of a false beyond-limit segment', () => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51]);
  expect(rfReferenceLink(estimate)).toEqual({ paths: [], limit: null, distanceKm: null });
  expect(rfReferenceLink({ ...estimate, receiver: estimate.origin })).toEqual({
    paths: [],
    limit: null,
    distanceKm: 0,
  });
  for (const fraction of [0.5, 1]) {
    const receiver = rfReferencePoint(estimate.origin, 30, estimate.radiusKm * fraction);
    const result = rfReferenceLink({ ...estimate, receiver });
    expect(result.limit).toBeNull();
    expect(result.paths.map(({ status }) => status)).toEqual(['inside']);
    expect(result.distanceKm).toBeCloseTo(estimate.radiusKm * fraction, 8);
  }
});

it.each<Position>([
  [179.9, 0],
  [-179.9, 70],
  [0, 89.9],
])('splits a geodesic at the radius across date lines and near poles from %s', (lon, lat) => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [lon, lat]);
  const receiver = rfReferencePoint(estimate.origin, 75, estimate.radiusKm * 2);
  const result = rfReferenceLink({ ...estimate, receiver });
  expect(result.paths.map(({ status }) => status)).toEqual(['inside', 'outside']);
  expect(result.paths.every(({ path }) => path.length === 65)).toBe(true);
  const limit = result.limit!;
  expect(Geodesic.WGS84.Inverse(lat, lon, limit[1], limit[0]).s12).toBeCloseTo(
    estimate.radiusKm * 1000,
    5,
  );
});

it('splits Mercator paths without connecting across excluded polar vertices', () => {
  const path: Position[] = [
    [0, 84],
    [1, 85],
    [2, 86],
    [3, 85],
    [4, 84],
  ];
  const segments = [{ path, status: 'inside' as const }];
  expect(rfReferencePaths(segments, true)).toEqual([
    { path: path.slice(0, 2), status: 'inside' },
    { path: path.slice(3), status: 'inside' },
  ]);
  expect(rfReferencePaths(segments, false)).toEqual(segments);
});

it('clips bubble sectors conservatively to the map and leaves near-pole globe geometry finite', () => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 85]);
  const ring = rfRangeRing(estimate);
  const clipped = rfReferenceBubble(estimate, ring, true);
  expect(clipped.length).toBeGreaterThan(0);
  expect(clipped.length).toBeLessThan(72);
  expect(clipped.flat().every((point) => Math.abs(point[1]) <= 85.05112878)).toBe(true);
  expect(rfReferenceBubble(estimate, ring, false)).toHaveLength(72);
  const southernPole = rfMapEstimate(DEFAULT_RF_INPUTS, [90, -90]);
  expect(rfReferenceBubble(southernPole, rfRangeRing(southernPole), false)).toEqual([]);
});

it('uses metres for short reference limits and kilometres for longer distances', () => {
  expect(rfReferenceDistance(0.001)).toBe('1 m');
  expect(rfReferenceDistance(0.125)).toBe('125 m');
  expect(rfReferenceDistance(12.345)).toBe('12.3 km');
});
