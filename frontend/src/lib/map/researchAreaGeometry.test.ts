import { expect, it } from 'vitest';
import { researchAreaGeometry } from './researchAreaGeometry';
import { researchAreaLayers } from './researchAreaLayers';
import type { Position } from './geoJsonTypes';

it('keeps a concave polygon instead of replacing it with a rectangle', () => {
  const anchors: Position[] = [
    [0, 0],
    [2, 0],
    [1, 1],
    [2, 2],
    [0, 2],
  ];
  const area = researchAreaGeometry('polygon', anchors);
  expect(area.features[0]?.geometry).toEqual({
    type: 'Polygon',
    coordinates: [[...anchors, [0, 0]]],
  });
  expect(anchors).toHaveLength(5);
});

it('splits a dateline rectangle while excluding the rest of the world', () => {
  const area = researchAreaGeometry('rectangle', [
    [179, -1],
    [-179, 1],
  ]);
  const geometry = area.features[0]?.geometry;
  expect(geometry?.type).toBe('MultiPolygon');
  if (geometry?.type !== 'MultiPolygon') throw new Error('Expected two polygons');
  expect(geometry.coordinates).toHaveLength(2);
  expect(geometry.coordinates.flat(2).every(([lon]) => Math.abs(lon) >= 179)).toBe(true);
});

it('makes a bounded circle polygon and refuses unfinished, crossing or zero-size areas', () => {
  const area = researchAreaGeometry('circle', [
    [0, 51],
    [0.1, 51],
  ]);
  expect(area.features[0]?.geometry).toMatchObject({ type: 'Polygon' });
  if (area.features[0]?.geometry.type === 'Polygon')
    expect(area.features[0].geometry.coordinates[0]).toHaveLength(33);
  expect(() =>
    researchAreaGeometry('polygon', [
      [0, 0],
      [1, 1],
    ]),
  ).toThrow('three corners');
  expect(() =>
    researchAreaGeometry('path', [
      [0, 0],
      [1, 1],
    ]),
  ).toThrow('polygon');
  expect(() => researchAreaGeometry('circle', [[0, 0]])).toThrow('complete');
  expect(() =>
    researchAreaGeometry('rectangle', [
      [0, 0],
      [0, 1],
    ]),
  ).toThrow('non-zero');
  expect(() =>
    researchAreaGeometry('polygon', [
      [0, 0],
      [2, 2],
      [2, 0],
      [0, 2],
    ]),
  ).toThrow('intersects');
  expect(() =>
    researchAreaGeometry('polygon', [
      [179, 0],
      [-179, 0],
      [179, 1],
    ]),
  ).toThrow('180°');
  expect(() =>
    researchAreaGeometry('circle', [
      [0, 0],
      [90, 0],
    ]),
  ).toThrow('1,000 km');
});

it.each([true, false])(
  'renders the exact canonical area with separate non-pickable IDs (flat=%s)',
  (flat) => {
    const anchors: Position[] = [
      [0, 0],
      [2, 0],
      [1, 1],
      [0, 2],
    ];
    const layers = researchAreaLayers('polygon', anchors, flat);
    expect(
      layers.every((layer) => layer.id.startsWith('research-area-') && !layer.props.pickable),
    ).toBe(true);
    expect(layers.find((layer) => layer.id === 'research-area-boundary')?.props.data).toEqual(
      researchAreaGeometry('polygon', anchors),
    );
    expect(researchAreaLayers('polygon', [], flat)).toEqual([]);
    expect(
      researchAreaLayers('polygon', [[0, 0]], flat).some(
        (layer) => layer.id === 'research-area-draft',
      ),
    ).toBe(true);
  },
);
