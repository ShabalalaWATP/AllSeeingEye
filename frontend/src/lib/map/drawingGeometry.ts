import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';

export type DrawingShape = 'path' | 'polygon' | 'rectangle' | 'circle';
export const DRAWING_SHAPES: readonly {
  value: DrawingShape;
  label: string;
  instruction: string;
}[] = [
  { value: 'path', label: 'Path', instruction: 'Click each waypoint, then finish drawing.' },
  {
    value: 'polygon',
    label: 'Polygon',
    instruction: 'Click at least three corners, then finish drawing.',
  },
  {
    value: 'rectangle',
    label: 'Rectangle',
    instruction: 'Click two opposite corners. Edges use shortest geodesic paths.',
  },
  {
    value: 'circle',
    label: 'Radius circle',
    instruction: 'Click the centre, then a point on the radius (maximum 1,000 km).',
  },
];

export function drawingVertices(shape: DrawingShape, anchors: readonly Position[]): Position[] {
  anchors.forEach(([lon, lat]) => measurementPoint(lon, lat));
  if (anchors.length > 32) throw new Error('At most 32 drawing points.');
  const [first, second] = anchors;
  if (!first || !second || shape === 'path' || shape === 'polygon') return [...anchors];
  if (shape === 'rectangle') return [first, [second[0], first[1]], second, [first[0], second[1]]];
  const radius = Geodesic.WGS84.Inverse(first[1], first[0], second[1], second[0]).s12 ?? NaN;
  if (!Number.isFinite(radius) || radius <= 0 || radius > 1e6)
    throw new Error('Choose a radius greater than zero and no more than 1,000 km.');
  // 32 vertices keeps rendering within the existing bounded measurement renderer.
  return Array.from({ length: 32 }, (_, index) => {
    const point = Geodesic.WGS84.Direct(first[1], first[0], (index * 360) / 32, radius);
    return measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
  });
}
