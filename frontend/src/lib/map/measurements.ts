import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';

export const MAX_MEASUREMENT_POINTS = 32;
export type MeasurementMode = 'distance' | 'area';

export function measurementPoint(longitude: number, latitude: number): Position {
  if (
    !Number.isFinite(longitude) ||
    !Number.isFinite(latitude) ||
    Math.abs(longitude) > 180 ||
    Math.abs(latitude) > 90
  )
    throw new Error('Enter longitude from -180 to 180 and latitude from -90 to 90.');
  return [longitude, latitude];
}

/** Ellipsoidal surface measurements, independent of display projection or terrain. */
export function measure(points: readonly Position[], mode: MeasurementMode) {
  if (points.length > MAX_MEASUREMENT_POINTS) throw new Error('At most 32 measurement points.');
  const polygon = Geodesic.WGS84.Polygon(mode === 'distance');
  for (const point of points) {
    const [lon, lat] = measurementPoint(point[0], point[1]);
    polygon.AddPoint(lat, lon);
  }
  const result = polygon.Compute(false, true);
  return {
    metres: result.perimeter,
    squareMetres: mode === 'area' && points.length >= 3 ? Math.abs(result.area ?? 0) : null,
  };
}

/** Bounded display sampling only; the result above uses the full geodesic solution. */
export function measurementPaths(points: readonly Position[], mode: MeasurementMode): Position[][] {
  measure(points, mode);
  const first = points[0];
  if (points.length < 2 || !first) return [];
  const vertices = mode === 'area' && points.length >= 3 ? [...points, first] : points;
  return vertices.slice(1).map((end, index) => {
    const start = vertices[index] ?? first;
    const line = Geodesic.WGS84.InverseLine(start[1], start[0], end[1], end[0]);
    // 64 intervals per edge, at most 2,080 generated positions for 32 vertices.
    return Array.from({ length: 65 }, (_, step): Position => {
      const point = line.Position((line.s13 * step) / 64);
      return measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
    });
  });
}

export function measurementText(points: readonly Position[], mode: MeasurementMode): string {
  const value = measure(points, mode);
  if (points.length < (mode === 'area' ? 3 : 2)) return 'Add more points to measure';
  return mode === 'distance'
    ? `${(value.metres / 1000).toFixed(3)} km`
    : `${((value.squareMetres ?? 0) / 1e6).toFixed(3)} km² · perimeter ${(value.metres / 1000).toFixed(3)} km`;
}
