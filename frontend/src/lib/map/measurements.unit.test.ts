import { expect, it } from 'vitest';
import { measure, measurementPaths, measurementPoint, measurementText } from './measurements';
import type { Position } from './geoJsonTypes';

it('measures the WGS84 equatorial arc rather than projected screen distance', () => {
  expect(
    measure(
      [
        [0, 0],
        [1, 0],
      ],
      'distance',
    ).metres,
  ).toBeCloseTo(111319.490793, 5);
  expect(
    measure(
      [
        [179, 0],
        [-179, 0],
      ],
      'distance',
    ).metres,
  ).toBeCloseTo(222638.981586, 5);
  expect(
    measure(
      [
        [0, 90],
        [180, 90],
      ],
      'distance',
    ).metres,
  ).toBeCloseTo(0, 8);
  expect(
    measure(
      [
        [0, 0],
        [180, 0],
      ],
      'distance',
    ).metres,
  ).toBeCloseTo(20003931.458625, 5);
});
it('closes polygon area with direction-independent net area and separate perimeter', () => {
  const square: Position[] = [
    [0, 0],
    [1, 0],
    [1, 1],
    [0, 1],
  ];
  expect(measure(square, 'area').squareMetres).toBeCloseTo(12308778361.469, 2);
  expect(measure([...square].reverse(), 'area')).toEqual(measure(square, 'area'));
  expect(measure(square, 'area').metres).toBeGreaterThan(measure(square, 'distance').metres);
  expect(measure([], 'area').squareMetres).toBeNull();
});
it('bounds and validates coordinates and preserves them while sampling geodesics', () => {
  for (const point of [
    [NaN, 0],
    [181, 0],
    [0, 91],
  ])
    expect(() => measurementPoint(point[0]!, point[1]!)).toThrow();
  expect(() =>
    measure(
      Array.from({ length: 33 }, (): Position => [0, 0]),
      'distance',
    ),
  ).toThrow();
  const points: Position[] = [
    [170, 60],
    [-170, 60],
  ];
  const paths = measurementPaths(points, 'distance');
  expect(paths[0]).toHaveLength(65);
  expect(paths[0]![32]![1]).toBeGreaterThan(60);
  expect(points).toEqual([
    [170, 60],
    [-170, 60],
  ]);
  expect(measurementPaths([], 'area')).toEqual([]);
  expect(measurementText([], 'distance')).toContain('Add more');
  expect(
    measurementText(
      [
        [0, 0],
        [1, 0],
      ],
      'distance',
    ),
  ).toBe('111.319 km');
});
