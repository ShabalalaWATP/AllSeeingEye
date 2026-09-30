import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { hitsDrawing, moveDrawing } from './drawingMove';
import { drawingLayers } from './drawingLayers';
import { drawingVertices } from './drawingGeometry';
import type { Position } from './geoJsonTypes';

it('moves sketches across the dateline and rejects latitude overflow', () => {
  expect(
    moveDrawing(
      'path',
      [
        [179, 10],
        [-179, 11],
      ],
      [179, 10],
      [-179, 12],
    ),
  ).toEqual([
    [-179, 12],
    [-177, 13],
  ]);
  expect(() =>
    moveDrawing(
      'path',
      [
        [0, 89],
        [1, 90],
      ],
      [0, 89],
      [0, 90],
    ),
  ).toThrow(/latitude/);
});
it('retains a circle radius when its centre changes latitude', () => {
  const moved = moveDrawing(
    'circle',
    [
      [0, 0],
      [1, 0],
    ],
    [0, 0],
    [10, 60],
  );
  expect(moved[0]).toEqual([10, 60]);
  expect(
    Geodesic.WGS84.Inverse(moved[0]![1], moved[0]![0], moved[1]![1], moved[1]![0]).s12,
  ).toBeCloseTo(111319.491, 2);
});
it('hits the filled dateline sketch without selecting the opposite side of Earth', () => {
  const anchors: Position[] = [
    [179, 0],
    [-179, 2],
  ];
  expect(hitsDrawing('rectangle', anchors, [180, 1], 0.01)).toBe(true);
  expect(hitsDrawing('rectangle', anchors, [0, 1], 0.01)).toBe(false);
  expect(
    hitsDrawing(
      'path',
      [
        [179, 0],
        [-179, 0],
      ],
      [0, 0],
      0.01,
    ),
  ).toBe(false);
  expect(
    hitsDrawing(
      'path',
      [
        [179, 0],
        [-179, 0],
      ],
      [-180, 0],
      0.01,
    ),
  ).toBe(true);
  expect(
    hitsDrawing(
      'path',
      [
        [0, 0],
        [1, 0],
      ],
      [0.5, 0.001],
      0.01,
    ),
  ).toBe(true);
  expect(hitsDrawing('polygon', [], [0, 0], 1)).toBe(false);
});
it.each([true, false])('keeps dateline fill longitude continuous, flat=%s', (flat) => {
  const points = drawingVertices('rectangle', [
    [179, 0],
    [-179, 2],
  ]);
  const fill = drawingLayers(points, 'area', flat).find((layer) => layer.id === 'drawing-fill');
  const ring = (fill?.props.data as Position[][])[0]!;
  expect(ring.map(([lon]) => lon)).toEqual([179, 181, 181, 179]);
  expect(points.map(([lon]) => lon)).toEqual([179, -179, -179, 179]);
});
