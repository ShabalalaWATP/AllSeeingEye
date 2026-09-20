import { expect, it } from 'vitest';
import {
  emptyDrawingCollection,
  exportDrawingGeoJson,
  importDrawingGeoJson,
  newDrawingObject,
  validateDrawingCollection,
  validateDrawingObject,
} from './drawingCollection';

it('round-trips named points, lines and polygons without losing labels or coordinates', () => {
  const objects = [
    newDrawingObject('point', [[-2, 54]], 0),
    newDrawingObject(
      'path',
      [
        [0, 0],
        [1, 1],
      ],
      1,
    ),
    newDrawingObject(
      'polygon',
      [
        [0, 0],
        [1, 0],
        [1, 1],
      ],
      2,
    ),
  ];
  const collection = { ...emptyDrawingCollection, objects };
  const restored = importDrawingGeoJson(exportDrawingGeoJson(collection));
  expect(restored.objects.map((item) => item.anchors)).toEqual(objects.map((item) => item.anchors));
  expect(restored.objects.map((item) => item.name)).toEqual(objects.map((item) => item.name));
  expect(restored.objects[0]?.id).not.toBe(objects[0]?.id);
});
it('rejects unbounded collections, duplicate IDs and invalid geometry rather than silently repairing', () => {
  const point = newDrawingObject('point', [[0, 0]], 0);
  expect(() =>
    validateDrawingCollection({ ...emptyDrawingCollection, objects: Array(51).fill(point) }),
  ).toThrow(/50/);
  expect(() =>
    validateDrawingCollection({ ...emptyDrawingCollection, objects: [point, point] }),
  ).toThrow(/unique/);
  expect(() => validateDrawingObject({ ...point, anchors: [[Infinity, 0]] })).toThrow();
  expect(() => validateDrawingObject({ ...point, anchors: [[181, 0]] })).toThrow();
  expect(() => validateDrawingObject({ ...point, colour: 'url(evil)' })).toThrow(/colour/);
  expect(() =>
    newDrawingObject(
      'polygon',
      [
        [0, 0],
        [1, 1],
        [0, 1],
        [1, 0],
      ],
      0,
    ),
  ).toThrow();
  expect(() =>
    newDrawingObject(
      'rectangle',
      [
        [0, 0],
        [0, 1],
      ],
      0,
    ),
  ).toThrow(/width/);
});
it('rejects holes, unsupported geometry, alternate CRS, oversized text and unclosed polygon rings', () => {
  const encode = (geometry: unknown) =>
    JSON.stringify({
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry, properties: {} }],
    });
  expect(() =>
    importDrawingGeoJson(encode({ type: 'GeometryCollection', geometries: [] })),
  ).toThrow(/Supported/);
  expect(() =>
    importDrawingGeoJson(
      encode({
        type: 'Polygon',
        coordinates: [
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
        ],
      }),
    ),
  ).toThrow(/closed/);
  expect(() => importDrawingGeoJson(encode({ type: 'Polygon', coordinates: [[], []] }))).toThrow(
    /holes/,
  );
  expect(() =>
    importDrawingGeoJson(JSON.stringify({ type: 'FeatureCollection', features: [], crs: {} })),
  ).toThrow(/WGS84/);
  expect(() => importDrawingGeoJson(' '.repeat(128 * 1024 + 1))).toThrow(/128 KiB/);
});
