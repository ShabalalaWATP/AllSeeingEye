import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import { measurementPaths, measurementPoint } from './measurements';
import type { RfMapEstimate } from './rfMap';

export interface RfReferencePath {
  path: Position[];
  status: 'inside' | 'outside' | 'boundary' | 'range';
}

const MERCATOR_LIMIT = 85.05112878;

export function rfReferenceDistance(distanceKm: number): string {
  return distanceKm < 1 ? `${Math.round(distanceKm * 1000)} m` : `${distanceKm.toFixed(1)} km`;
}

export function rfReferencePoint(origin: Position, bearing: number, distanceKm: number): Position {
  const point = Geodesic.WGS84.Direct(origin[1], origin[0], bearing, distanceKm * 1000);
  return measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
}

/** A display split at the existing ideal model limit, never a terrain obstruction claim. */
export function rfReferenceLink(estimate: RfMapEstimate) {
  const { origin, receiver, radiusKm } = estimate;
  const paths: RfReferencePath[] = [];
  if (!receiver) return { paths, limit: null, distanceKm: null };
  const inverse = Geodesic.WGS84.Inverse(origin[1], origin[0], receiver[1], receiver[0]);
  const distanceKm = (inverse.s12 ?? 0) / 1000;
  if (distanceKm < 0.000001) return { paths, limit: null, distanceKm };
  // A micrometre tolerance avoids a spurious red segment at the exact boundary.
  const limit =
    distanceKm > radiusKm + 1e-9 ? rfReferencePoint(origin, inverse.azi1 ?? 0, radiusKm) : null;
  for (const path of measurementPaths([origin, limit ?? receiver], 'distance'))
    paths.push({ path, status: 'inside' });
  if (limit)
    for (const path of measurementPaths([limit, receiver], 'distance'))
      paths.push({ path, status: 'outside' });
  return { paths, limit, distanceKm };
}

export function rfReferenceVisible(point: Position, flat: boolean): boolean {
  return !flat || Math.abs(point[1]) <= MERCATOR_LIMIT;
}

/** Preserve globe positions and split paths before Web Mercator becomes undefined. */
export function rfReferencePaths(paths: RfReferencePath[], flat: boolean): RfReferencePath[] {
  return paths.flatMap((segment) => {
    const pieces: Position[][] = [[]];
    for (const point of segment.path) {
      if (rfReferenceVisible(point, flat)) pieces[pieces.length - 1]?.push(point);
      else pieces.push([]);
    }
    return pieces.filter((path) => path.length > 1).map((path) => ({ ...segment, path }));
  });
}

/** Fixed-size static wedges keep the bubble bounded and safe at the antimeridian. */
export function rfReferenceBubble(
  estimate: RfMapEstimate,
  ring: Position[],
  flat: boolean,
): Position[][] {
  const { origin } = estimate;
  const pole = origin[1] >= 0 ? 90 : -90;
  const poleDistanceKm = (Geodesic.WGS84.Inverse(origin[1], origin[0], pole, 0).s12 ?? 0) / 1000;
  // A ring surrounding a pole cannot be represented by a simple longitude fan.
  // Retain its outline on the globe but omit fill rather than shade the wrong hemisphere.
  if (estimate.radiusKm >= poleDistanceKm) return [];
  return ring.slice(1).flatMap((point, index) => {
    const previous = ring[index];
    if (!previous) return [];
    const polygon = [origin, previous, point, origin].map(([lon, lat]): Position => [
      lon + 360 * Math.round((origin[0] - lon) / 360),
      lat,
    ]);
    const longitudes = polygon.map(([lon]) => lon);
    return polygon.every((vertex) => rfReferenceVisible(vertex, flat)) &&
      Math.max(...longitudes) - Math.min(...longitudes) <= 180
      ? [polygon]
      : [];
  });
}
