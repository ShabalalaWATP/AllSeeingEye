import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import { drawingVertices, type DrawingShape } from './drawingGeometry';
import { measurementPoint } from './measurements';

const wrap = (longitude: number) => ((((longitude + 180) % 360) + 360) % 360) - 180;

/** Longitude/latitude translation; circles retain their geodesic radius. */
export function moveDrawing(
  shape: DrawingShape,
  anchors: readonly Position[],
  start: Position,
  end: Position,
): Position[] {
  const delta: Position = [wrap(end[0] - start[0]), end[1] - start[1]];
  const moved = anchors.map(([lon, lat]) => measurementPoint(wrap(lon + delta[0]), lat + delta[1]));
  if (shape === 'circle' && anchors[0] && anchors[1] && moved[0]) {
    const radius = Geodesic.WGS84.Inverse(
      anchors[0][1],
      anchors[0][0],
      anchors[1][1],
      anchors[1][0],
    );
    const edge = Geodesic.WGS84.Direct(
      moved[0][1],
      moved[0][0],
      radius.azi1 ?? NaN,
      radius.s12 ?? NaN,
    );
    moved[1] = measurementPoint(edge.lon2 ?? NaN, edge.lat2 ?? NaN);
  }
  drawingVertices(shape, moved);
  return moved;
}

/** Hit the filled sketch or a nearby path/handle, with dateline-aware coordinates. */
export function hitsDrawing(
  shape: DrawingShape,
  anchors: readonly Position[],
  point: Position,
  tolerance: number,
): boolean {
  const vertices = drawingVertices(shape, anchors).map(
    ([lon, lat]) => [wrap(lon - point[0]), lat - point[1]] as Position,
  );
  // Keep neighbouring vertices in the same world copy. Independent wrapping makes
  // a narrow dateline rectangle appear to include Greenwich in a planar hit test.
  for (const [i, vertex] of vertices.entries()) {
    const previous = vertices[i - 1];
    if (previous) vertex[0] = previous[0] + wrap(vertex[0] - previous[0]);
  }
  const scale = Math.max(0.1, Math.cos((point[1] * Math.PI) / 180));
  let inside = false;
  for (const [i, a] of vertices.entries()) {
    const b = vertices[(i + 1) % vertices.length] ?? a;
    if (Math.hypot(a[0] * scale, a[1]) <= tolerance) return true;
    if (
      shape !== 'path' &&
      a[1] > 0 !== b[1] > 0 &&
      0 < a[0] + (-a[1] * (b[0] - a[0])) / (b[1] - a[1])
    )
      inside = !inside;
    if (shape === 'path' && i < vertices.length - 1) {
      const dx = (b[0] - a[0]) * scale;
      const dy = b[1] - a[1];
      const t = Math.max(
        0,
        Math.min(1, -(a[0] * scale * dx + a[1] * dy) / (dx * dx + dy * dy || 1)),
      );
      if (Math.hypot(a[0] * scale + t * dx, a[1] + t * dy) <= tolerance) return true;
    }
  }
  return inside;
}
