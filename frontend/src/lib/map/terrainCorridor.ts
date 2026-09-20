import { Geodesic } from 'geographiclib-geodesic';
import { measurementPoint } from './measurements';
import { parseLocalGeoJson } from './localGeoJson';
import type { LocalCollection, Position } from './geoJsonTypes';

const angleDifference = (first: number, second: number) => ((second - first + 540) % 360) - 180;
function pointAt(points: readonly Position[], index: number): Position {
  const point = points[index];
  if (!point) throw new Error('The corridor path is incomplete.');
  return point;
}
function offset(point: Position, bearing: number, metres: number): Position {
  const next = Geodesic.WGS84.Direct(point[1], point[0], bearing, metres);
  return measurementPoint(next.lon2 ?? NaN, next.lat2 ?? NaN);
}

/** A bounded approximate corridor, with geodesic offsets, miter joins and sampled caps.
 * The generated polygon is the actual research boundary; topology is never repaired
 * by silently replacing it with an enclosing rectangle or simplified route.
 */
export function createResearchCorridor(
  path: readonly Position[],
  halfWidthKm: number,
): LocalCollection {
  if (path.length < 2 || path.length > 32)
    throw new Error(
      'Choose a path with 2–32 points. Long route geometries must be simplified explicitly first.',
    );
  if (!Number.isFinite(halfWidthKm) || halfWidthKm < 0.01 || halfWidthKm > 20)
    throw new Error('Distance on each side must be from 0.01 to 20 km.');
  const points = path.map((point) => measurementPoint(...point));
  if (points.some((point) => Math.abs(point[1]) > 80))
    throw new Error('Corridors are limited to latitudes between 80°S and 80°N.');
  const sampled: Position[] = [pointAt(points, 0)];
  let lengthM = 0;
  for (let i = 1; i < points.length; i++) {
    const start = pointAt(points, i - 1),
      end = pointAt(points, i);
    if (Math.abs(end[0] - start[0]) > 180)
      throw new Error('Corridors crossing 180° longitude need a pre-split area instead.');
    const line = Geodesic.WGS84.InverseLine(start[1], start[0], end[1], end[0]);
    if (line.s13 < 1) throw new Error('Consecutive path points must be at least one metre apart.');
    lengthM += line.s13;
    if (lengthM > 200000) throw new Error('Research corridors are limited to 200 km of path.');
    const steps = Math.ceil(line.s13 / 5000);
    for (let step = 1; step <= steps; step++) {
      const point = line.Position((line.s13 * step) / steps);
      sampled.push(step === steps ? end : measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN));
    }
  }
  const segments = sampled.slice(1).map((end, i) => {
    const start = pointAt(sampled, i);
    return Geodesic.WGS84.Inverse(start[1], start[0], end[1], end[0]);
  });
  const halfWidthM = halfWidthKm * 1000;
  const left: Position[] = [],
    right: Position[] = [];
  for (let i = 0; i < sampled.length; i++) {
    const incoming = segments[i - 1]?.azi2 ?? segments[i]?.azi1 ?? NaN;
    const outgoing = segments[i]?.azi1 ?? incoming;
    const turn = angleDifference(incoming, outgoing);
    const multiplier = 1 / Math.cos((turn * Math.PI) / 360);
    if (!Number.isFinite(multiplier) || multiplier > 3)
      throw new Error(
        'This path turns too sharply for a reliable corridor. Split it into separate shorter paths.',
      );
    const bearing = incoming + turn / 2;
    left.push(offset(pointAt(sampled, i), bearing - 90, halfWidthM * multiplier));
    right.push(offset(pointAt(sampled, i), bearing + 90, halfWidthM * multiplier));
  }
  const ring = [...left];
  const end = pointAt(sampled, sampled.length - 1),
    endBearing = segments.at(-1)?.azi2 ?? NaN;
  for (let step = 1; step <= 12; step++)
    ring.push(offset(end, endBearing - 90 + (180 * step) / 12, halfWidthM));
  ring.push(...right.slice(0, -1).reverse());
  const start = pointAt(sampled, 0),
    startBearing = segments[0]?.azi1 ?? NaN;
  for (let step = 1; step < 12; step++)
    ring.push(offset(start, startBearing + 90 + (180 * step) / 12, halfWidthM));
  ring.push(pointAt(ring, 0));
  const text = JSON.stringify({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { label: `Corridor, ${halfWidthKm} km each side` },
        geometry: { type: 'Polygon', coordinates: [ring] },
      },
    ],
  });
  if (new TextEncoder().encode(text).byteLength > 16 * 1024 || ring.length > 256)
    throw new Error(
      'The corridor exceeds the research boundary size limit. Choose a shorter path.',
    );
  try {
    return parseLocalGeoJson(text).canonical;
  } catch (failure) {
    throw new Error(
      `Cannot use this corridor: ${failure instanceof Error ? failure.message : 'invalid boundary'} Reduce its width or choose a simpler path.`,
    );
  }
}
