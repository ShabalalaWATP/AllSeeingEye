import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { drawingVertices } from './drawingGeometry';
import { drawingLayers } from './drawingLayers';

it('builds rectangles and retains path vertices', () => {
  expect(
    drawingVertices('rectangle', [
      [170, 0],
      [-170, 10],
    ]),
  ).toEqual([
    [170, 0],
    [-170, 0],
    [-170, 10],
    [170, 10],
  ]);
  expect(drawingVertices('path', [[1, 2]])).toEqual([[1, 2]]);
  expect(drawingVertices('polygon', [])).toEqual([]);
});
it('samples a geodesic circle at a constant radius and bounds expensive geometry', () => {
  const points = drawingVertices('circle', [
    [0, 0],
    [0.1, 0],
  ]);
  expect(points).toHaveLength(32);
  for (const point of points)
    expect(Geodesic.WGS84.Inverse(0, 0, point[1], point[0]).s12).toBeCloseTo(11131.949, 1);
  expect(() =>
    drawingVertices('circle', [
      [0, 0],
      [0, 0],
    ]),
  ).toThrow(/radius/);
  expect(() =>
    drawingVertices('circle', [
      [0, 0],
      [30, 0],
    ]),
  ).toThrow(/radius/);
  expect(() =>
    drawingVertices(
      'path',
      Array.from({ length: 33 }, () => [0, 0]),
    ),
  ).toThrow(/32/);
});
it('uses independent non-pickable drawing layer IDs', () => {
  const layers = drawingLayers(
    [
      [0, 0],
      [1, 1],
    ],
    'distance',
    false,
  );
  expect(layers.map((layer) => layer.id)).toEqual([
    'drawing-measurement-path',
    'drawing-measurement-points',
  ]);
  expect(layers.every((layer) => !layer.props.pickable)).toBe(true);
});
