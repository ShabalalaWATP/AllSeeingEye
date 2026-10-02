import { expect, it } from 'vitest';
import {
  geometryIsPolar,
  geometryVertices,
  MAX_GEOJSON_VERTICES,
  parseLocalGeoJson,
} from './localGeoJson';
import type { LocalGeometry, Position } from './geoJsonTypes';

const feature = (geometry: unknown, properties: unknown = null) => ({
  type: 'Feature',
  geometry,
  properties,
});
const collection = (features: unknown[]) => JSON.stringify({ type: 'FeatureCollection', features });

it.each([null, [], 42, 'not an object'])('rejects a non-object document root %j', (value) => {
  expect(() => parseLocalGeoJson(JSON.stringify(value))).toThrow('Expected a GeoJSON object');
});

it('requires a collection wrapper and Feature entries instead of silently accepting bare geometry', () => {
  const geometry = { type: 'Point', coordinates: [0, 0] };
  expect(() => parseLocalGeoJson(JSON.stringify(feature(geometry)))).toThrow(
    'Import a GeoJSON FeatureCollection',
  );
  expect(() => parseLocalGeoJson(collection([geometry]))).toThrow(
    'Every collection entry must be a Feature',
  );
});

it('uses a title label when the name is not text and drops unrelated properties', () => {
  const parsed = parseLocalGeoJson(
    collection([
      feature(
        { type: 'Point', coordinates: [0, 0] },
        { name: 123, title: 'Boundary observation', label: 'Lower priority', secret: 'discard' },
      ),
    ]),
  );
  expect(parsed.canonical.features[0]?.properties).toEqual({ label: 'Boundary observation' });
});

it.each(['geometry', 'properties', 'feature'] as const)(
  'rejects malformed objects in the %s boundary',
  (target) => {
    const input = feature({ type: 'Point', coordinates: [1, 2] });
    const malformed = target === 'feature' ? [] : { ...input, [target]: [] };
    expect(() => parseLocalGeoJson(collection([malformed]))).toThrow('Expected a GeoJSON object');
  },
);

it('retains independent lines and splits only the antimeridian crossing for display', () => {
  const coordinates: Position[][] = [
    [
      [1, 2],
      [3, 4],
    ],
    [
      [-170, 10],
      [170, 30],
    ],
  ];
  const parsed = parseLocalGeoJson(collection([feature({ type: 'MultiLineString', coordinates })]));
  expect(parsed.vertices).toBe(4);
  expect(parsed.canonical.features[0]?.geometry).toEqual({ type: 'MultiLineString', coordinates });
  expect(parsed.display.features[0]?.geometry).toEqual({
    type: 'MultiLineString',
    coordinates: [
      [
        [1, 2],
        [3, 4],
      ],
      [
        [-170, 10],
        [-180, 20],
      ],
      [
        [180, 20],
        [170, 30],
      ],
    ],
  });
});

it('accepts absent properties and gives unnamed features stable numbered labels', () => {
  const geometry = { type: 'Point', coordinates: [0, 0] };
  const parsed = parseLocalGeoJson(collection([feature(geometry), { type: 'Feature', geometry }]));
  expect(parsed.canonical.features.map((item) => item.properties)).toEqual([
    { label: 'Feature 1' },
    { label: 'Feature 2' },
  ]);
});

it('enforces the shared vertex limit across multiple individually valid coordinate arrays', () => {
  const half = Array.from({ length: MAX_GEOJSON_VERTICES / 2 }, (): Position => [1, 2]);
  const first = feature({ type: 'MultiPoint', coordinates: half });
  expect(parseLocalGeoJson(collection([first, first])).vertices).toBe(MAX_GEOJSON_VERTICES);
  const second = feature({ type: 'MultiPoint', coordinates: [...half, [3, 4]] });
  expect(() => parseLocalGeoJson(collection([first, second]))).toThrow(
    'limited to 100,000 vertices',
  );
});

const shapes: { name: string; geometry: (latitude: number) => LocalGeometry; vertices: number }[] =
  [
    {
      name: 'point',
      geometry: (latitude) => ({ type: 'Point', coordinates: [1, latitude] }),
      vertices: 1,
    },
    {
      name: 'multipoint',
      geometry: (latitude) => ({
        type: 'MultiPoint',
        coordinates: [
          [0, 0],
          [1, latitude],
        ],
      }),
      vertices: 2,
    },
    {
      name: 'line',
      geometry: (latitude) => ({
        type: 'LineString',
        coordinates: [
          [0, 0],
          [1, latitude],
        ],
      }),
      vertices: 2,
    },
    {
      name: 'multiline',
      geometry: (latitude) => ({
        type: 'MultiLineString',
        coordinates: [
          [
            [0, 0],
            [1, 1],
          ],
          [
            [2, 2],
            [3, latitude],
          ],
        ],
      }),
      vertices: 4,
    },
    {
      name: 'polygon',
      geometry: (latitude) => ({
        type: 'Polygon',
        coordinates: [
          [
            [0, 0],
            [1, 0],
            [1, latitude],
            [0, 0],
          ],
        ],
      }),
      vertices: 4,
    },
    {
      name: 'multipolygon',
      geometry: (latitude) => ({
        type: 'MultiPolygon',
        coordinates: [
          [
            [
              [0, 0],
              [1, 0],
              [1, 1],
              [0, 0],
            ],
          ],
          [
            [
              [2, 2],
              [3, 2],
              [3, latitude],
              [2, 2],
            ],
          ],
        ],
      }),
      vertices: 8,
    },
  ];

it.each(shapes)(
  'detects polar coordinates and counts vertices throughout a $name',
  ({ geometry, vertices }) => {
    expect(geometryIsPolar(geometry(85.05112878))).toBe(false);
    expect(geometryIsPolar(geometry(86))).toBe(true);
    expect(geometryIsPolar(geometry(-86))).toBe(true);
    expect(geometryVertices(geometry(86))).toBe(vertices);
  },
);
