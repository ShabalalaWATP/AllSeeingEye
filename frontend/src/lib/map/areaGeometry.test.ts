import { expect, it } from 'vitest';
import { areaClickPoint, areasEqual, boundsFromCorners, rectangleArea } from './areaGeometry';

it('stores ordinary and wide rectangles without shortening their numeric longitude span', () => {
  const ordinary = rectangleArea({ west: 1, east: 3, south: 2, north: 4 });
  expect(ordinary.features[0]!.geometry).toEqual({
    type: 'Polygon',
    coordinates: [
      [
        [1, 2],
        [3, 2],
        [3, 4],
        [1, 4],
        [1, 2],
      ],
    ],
  });
  const world = rectangleArea({ west: -180, east: 180, south: -90, north: 90 });
  expect(world.features[0]!.geometry).toEqual({
    type: 'Polygon',
    coordinates: [
      [
        [-180, -90],
        [0, -90],
        [180, -90],
        [180, 90],
        [0, 90],
        [-180, 90],
        [-180, -90],
      ],
    ],
  });
});

it('splits a seam-crossing rectangle canonically, dropping only a zero-width seam fragment', () => {
  const split = rectangleArea({ west: 170, east: -170, south: -10, north: 10 });
  expect(split.features[0]!.geometry).toEqual({
    type: 'MultiPolygon',
    coordinates: [
      [
        [
          [170, -10],
          [180, -10],
          [180, 10],
          [170, 10],
          [170, -10],
        ],
      ],
      [
        [
          [-180, -10],
          [-170, -10],
          [-170, 10],
          [-180, 10],
          [-180, -10],
        ],
      ],
    ],
  });
  expect(
    rectangleArea({ west: 180, east: -170, south: 0, north: 1 }).features[0]!.geometry.type,
  ).toBe('Polygon');
});

it.each([
  { west: 0, east: 0, south: 0, north: 1 },
  { west: 180, east: -180, south: 0, north: 1 },
  { west: 0, east: 1, south: 2, north: 1 },
  { west: 0, east: 1, south: 1, north: 1 },
  { west: NaN, east: 1, south: 0, north: 1 },
  { west: 0, east: 181, south: 0, north: 1 },
  { west: 0, east: 1, south: -91, north: 1 },
])('rejects empty, inverted or non-WGS84 rectangles %j', (bounds) => {
  expect(() => rectangleArea(bounds)).toThrow();
});

it('uses the shorter explicit corner span and validates actual map click coordinates', () => {
  expect(boundsFromCorners([-170, 20], [170, 10])).toEqual({
    west: 170,
    east: -170,
    south: 10,
    north: 20,
  });
  expect(boundsFromCorners([3, 4], [1, 2])).toEqual({ west: 1, east: 3, south: 2, north: 4 });
  expect(areaClickPoint({ lngLat: { lng: 190, lat: 80 } })).toEqual([-170, 80]);
  for (const event of [
    null,
    {},
    { lngLat: null },
    { lngLat: { lng: '2', lat: 0 } },
    { lngLat: { lng: Infinity, lat: 0 } },
    { lngLat: { lng: 2, lat: 91 } },
  ])
    expect(areaClickPoint(event)).toBeNull();
});

it('compares area geometry independent of serializer key order', () => {
  const area = rectangleArea({ west: 1, east: 2, south: 3, north: 4 });
  expect(areasEqual(area, { features: area.features, type: 'FeatureCollection' })).toBe(true);
  expect(areasEqual(area, area)).toBe(true);
  expect(areasEqual(area, null)).toBe(false);
  expect(areasEqual(area, rectangleArea({ west: 1, east: 3, south: 3, north: 4 }))).toBe(false);
});
