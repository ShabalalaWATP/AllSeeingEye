import { expect, it } from 'vitest';
import { simplifyCorridorPath } from './terrainCorridorSimplification';
import { createResearchCorridor } from './terrainCorridor';
import type { Position } from './geoJsonTypes';

const route = Array.from({ length: 120 }, (_, index): Position => [
  index / 1000,
  51 + 0.001 * Math.sin(index / 20),
]);

it('preserves endpoints, bounds the approximation and does not modify the original route', () => {
  const original = JSON.stringify(route);
  const simplified = simplifyCorridorPath(route, 250);
  expect(simplified.points.length).toBeLessThanOrEqual(32);
  expect(simplified.points[0]).toEqual(route[0]);
  expect(simplified.points.at(-1)).toEqual(route.at(-1));
  expect(simplified.originalCount).toBe(120);
  expect(simplified.deviationBoundM).toBeGreaterThan(0);
  expect(simplified.deviationBoundM).toBeLessThanOrEqual(250);
  expect(JSON.stringify(route)).toBe(original);
  expect(createResearchCorridor(simplified.points, 0.1).features).toHaveLength(1);
});

it('rejects excessive original-path deviations rather than quietly increasing tolerance', () => {
  const zigzag = Array.from({ length: 100 }, (_, index): Position => [
    index * 0.001,
    index % 2 ? 0.002 : 0,
  ]);
  expect(() => simplifyCorridorPath(zigzag, 50)).toThrow(/can deviate by up to/);
});

it('rejects oversized, polar, dateline and excessive-length inputs before comparison', () => {
  expect(() =>
    simplifyCorridorPath(
      Array.from({ length: 10001 }, () => [0, 0]),
      250,
    ),
  ).toThrow(/10,000/);
  expect(() =>
    simplifyCorridorPath(
      [
        [179.99, 0],
        [-179.99, 0],
      ],
      250,
    ),
  ).toThrow(/180/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 85],
        [0.01, 85],
      ],
      250,
    ),
  ).toThrow(/80/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 0],
        [5, 0],
      ],
      250,
    ),
  ).toThrow(/200 km/);
  expect(() =>
    simplifyCorridorPath(
      [
        [0, 0],
        [0, 0],
      ],
      250,
    ),
  ).toThrow(/distinct/);
  expect(() => simplifyCorridorPath(route, NaN)).toThrow(/deviation/);
});

it('keeps a dense route within the explicit work budget', () => {
  const dense = Array.from({ length: 10000 }, (_, index): Position => [index / 100000, 0]);
  const simplified = simplifyCorridorPath(dense, 50);
  expect(simplified.points).toHaveLength(2);
  expect(simplified.deviationBoundM).toBeLessThanOrEqual(2);
});
