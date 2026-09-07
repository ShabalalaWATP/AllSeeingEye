import type { LocalGeometry, Position } from './geoJsonTypes';
import type { MapBounds } from './MapEngine';

function positionsOf(geometry: LocalGeometry): Position[] {
  switch (geometry.type) {
    case 'Point':
      return [geometry.coordinates];
    case 'MultiPoint':
    case 'LineString':
      return geometry.coordinates;
    case 'Polygon':
    case 'MultiLineString':
      return geometry.coordinates.flat();
    case 'MultiPolygon':
      return geometry.coordinates.flat(2);
  }
}

/** Minimum longitude envelope, including a wrapped envelope at the antimeridian. */
export function geometryBounds(geometry: LocalGeometry): MapBounds {
  const positions = positionsOf(geometry);
  // Each unsplit component occupies its complete longitude interval. A vertex-only
  // minimum arc can exclude edges or polygon interiors between those vertices.
  const parts: Position[][] =
    geometry.type === 'Point'
      ? [[geometry.coordinates]]
      : geometry.type === 'MultiPoint'
        ? geometry.coordinates.map((point) => [point])
        : geometry.type === 'MultiPolygon'
          ? geometry.coordinates.map((polygon) => polygon.flat())
          : geometry.type === 'MultiLineString'
            ? geometry.coordinates
            : [positions];
  const intervals = parts
    .map((part) => {
      let low = 180,
        high = -180;
      for (const [lon] of part) {
        low = Math.min(low, lon);
        high = Math.max(high, lon);
      }
      return [low, high] as [number, number];
    })
    .sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [];
  for (const interval of intervals) {
    const last = merged[merged.length - 1];
    if (last && interval[0] <= last[1]) last[1] = Math.max(last[1], interval[1]);
    else merged.push([...interval]);
  }
  const first = merged[0],
    last = merged[merged.length - 1];
  if (!first || !last) throw new Error('Geometry has no positions to fit.');
  let west = first[0],
    east = last[1];
  let gap = 360 - east + west;
  for (let i = 1; i < merged.length; i++) {
    const previousPart = merged[i - 1],
      nextPart = merged[i];
    if (!previousPart || !nextPart) throw new Error('Incomplete geometry bounds.');
    const previous = previousPart[1],
      next = nextPart[0];
    if (next - previous > gap) {
      gap = next - previous;
      west = next;
      east = previous;
    }
  }
  let south = 90,
    north = -90;
  for (const [, lat] of positions) {
    south = Math.min(south, lat);
    north = Math.max(north, lat);
  }
  return { west, south, east, north };
}
