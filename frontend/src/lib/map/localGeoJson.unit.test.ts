import { expect, it } from 'vitest';
import { parseLocalGeoJson, MAX_GEOJSON_BYTES, geometryIsPolar } from './localGeoJson';
const collection = (geometry: unknown, properties: unknown = {}) =>
  JSON.stringify({
    type: 'FeatureCollection',
    features: [{ type: 'Feature', geometry, properties }],
  });

it('round trips canonical overlay labels and seam geometry without retaining extra properties', () => {
  const imported = parseLocalGeoJson(
    collection(
      {
        type: 'LineString',
        coordinates: [
          [170, 10],
          [-170, 20],
        ],
      },
      { name: 'Reported project boundary', url: 'https://invalid.test/private' },
    ),
  );
  const restored = parseLocalGeoJson(JSON.stringify(imported.canonical));
  expect(restored).toEqual(imported);
  expect(restored.canonical.features[0]!.properties).toEqual({
    label: 'Reported project boundary',
  });
});

it('splits dateline lines for display without changing canonical evidence coordinates', () => {
  const parsed = parseLocalGeoJson(
    collection({
      type: 'LineString',
      coordinates: [
        [170, 10],
        [-170, 20],
      ],
    }),
  );
  expect(parsed.canonical.features[0]!.geometry).toEqual({
    type: 'LineString',
    coordinates: [
      [170, 10],
      [-170, 20],
    ],
  });
  expect(parsed.display.features[0]!.geometry).toEqual({
    type: 'MultiLineString',
    coordinates: [
      [
        [170, 10],
        [180, 15],
      ],
      [
        [-180, 15],
        [-170, 20],
      ],
    ],
  });
});
it.each([
  [{ type: 'Point', coordinates: [181, 1] }, /finite WGS84/],
  [{ type: 'Point', coordinates: [0, 0, 100] }, /Altitude/],
  [
    {
      type: 'Polygon',
      coordinates: [
        [
          [1, 1],
          [2, 2],
          [3, 1],
        ],
      ],
    },
    /closed/,
  ],
  [
    {
      type: 'Polygon',
      coordinates: [
        [
          [170, 0],
          [-170, 0],
          [-170, 10],
          [170, 0],
        ],
      ],
    },
    /pre-split/,
  ],
  [
    {
      type: 'Polygon',
      coordinates: [
        [
          [0, 0],
          [2, 2],
          [0, 2],
          [2, 0],
          [0, 0],
        ],
      ],
    },
    /intersects/,
  ],
  [{ type: 'GeometryCollection', geometries: [] }, /Unsupported geometry/],
])('rejects unsafe or unsupported geometry %j', (geometry, message) => {
  expect(() => parseLocalGeoJson(collection(geometry))).toThrow(message);
});
it('supports pre-split seam polygons, holes and original polar coordinates', () => {
  const parsed = parseLocalGeoJson(
    collection({
      type: 'MultiPolygon',
      coordinates: [
        [
          [
            [170, 0],
            [180, 0],
            [180, 10],
            [170, 10],
            [170, 0],
          ],
        ],
        [
          [
            [-180, 0],
            [-170, 0],
            [-170, 10],
            [-180, 10],
            [-180, 0],
          ],
        ],
      ],
    }),
  );
  expect(parsed.display).toEqual(parsed.canonical);
  expect(geometryIsPolar({ type: 'Point', coordinates: [10, 89] })).toBe(true);
  const holes = parseLocalGeoJson(
    collection({
      type: 'Polygon',
      coordinates: [
        [
          [0, 0],
          [10, 0],
          [10, 10],
          [0, 10],
          [0, 0],
        ],
        [
          [2, 2],
          [4, 2],
          [4, 4],
          [2, 4],
          [2, 2],
        ],
      ],
    }),
  );
  expect(holes.vertices).toBe(10);
});
it('rejects external CRS and holes outside the outer ring', () => {
  expect(() =>
    parseLocalGeoJson(
      JSON.stringify({ type: 'FeatureCollection', crs: 'EPSG:3857', features: [] }),
    ),
  ).toThrow(/WGS84/);
  expect(() =>
    parseLocalGeoJson(
      collection({
        type: 'Polygon',
        coordinates: [
          [
            [0, 0],
            [2, 0],
            [2, 2],
            [0, 2],
            [0, 0],
          ],
          [
            [4, 4],
            [5, 4],
            [5, 5],
            [4, 4],
          ],
        ],
      }),
    ),
  ).toThrow(/outside/);
});
it('bounds bytes, features and vertices, including display expansion', () => {
  expect(() => parseLocalGeoJson(' '.repeat(MAX_GEOJSON_BYTES + 1))).toThrow(/5 MiB/);
  const feature = { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 1] } };
  expect(() =>
    parseLocalGeoJson(
      JSON.stringify({
        type: 'FeatureCollection',
        features: Array.from({ length: 2001 }, () => feature),
      }),
    ),
  ).toThrow(/2,000/);
  expect(() =>
    parseLocalGeoJson(
      collection({ type: 'MultiPoint', coordinates: Array.from({ length: 100001 }, () => [1, 1]) }),
    ),
  ).toThrow(/oversized/);
  expect(() =>
    parseLocalGeoJson(
      collection({
        type: 'LineString',
        coordinates: Array.from({ length: 50000 }, (_, i) => [i % 2 ? -179 : 179, 1]),
      }),
    ),
  ).toThrow(/display-vertex/);
});
it('retains only a bounded plain label and ignores remote resources in properties', () => {
  const parsed = parseLocalGeoJson(
    collection(
      { type: 'Point', coordinates: [0, 0] },
      {
        name: '<script>literal</script>',
        url: 'https://invalid.test/data',
        nested: { secret: 'not retained' },
      },
    ),
  );
  expect(parsed.canonical.features[0]!.properties).toEqual({ label: '<script>literal</script>' });
});

it('bounds topology work across all polygons in one upload', () => {
  const ring = Array.from({ length: 255 }, (_, index) => {
    const angle = (index * 2 * Math.PI) / 255;
    return [Math.cos(angle), Math.sin(angle)];
  });
  ring.push(ring[0]!);
  const feature = {
    type: 'Feature',
    geometry: { type: 'Polygon', coordinates: [ring] },
  };
  expect(() =>
    parseLocalGeoJson(
      JSON.stringify({
        type: 'FeatureCollection',
        features: Array.from({ length: 40 }, () => feature),
      }),
    ),
  ).toThrow(/topology.*Simplify/);
});

it('truncates multilingual labels without splitting Unicode characters', () => {
  const parsed = parseLocalGeoJson(
    collection({ type: 'Point', coordinates: [0, 0] }, { name: '中'.repeat(299) + '🌍' + 'extra' }),
  );
  expect(parsed.canonical.features[0]!.properties.label).toBe('中'.repeat(299) + '🌍');
  expect(parseLocalGeoJson(JSON.stringify(parsed.canonical))).toEqual(parsed);
});
