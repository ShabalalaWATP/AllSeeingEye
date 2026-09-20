import { Geodesic } from 'geographiclib-geodesic';
import { measurementPoint } from './measurements';
import type { Position } from './geoJsonTypes';

export interface CorridorSimplification {
  points: Position[];
  originalCount: number;
  lengthKm: number;
  deviationBoundM: number;
}
interface PlanePoint {
  x: number;
  y: number;
}
function pointAt(points: readonly Position[], index: number): Position {
  const point = points[index];
  if (!point) throw new Error('The route is incomplete.');
  return point;
}
function onSegment(point: PlanePoint, start: PlanePoint, end: PlanePoint) {
  const dx = end.x - start.x,
    dy = end.y - start.y;
  const divisor = dx * dx + dy * dy;
  const fraction = divisor
    ? Math.min(1, Math.max(0, ((point.x - start.x) * dx + (point.y - start.y) * dy) / divisor))
    : 0;
  return {
    fraction,
    distance: Math.hypot(point.x - start.x - fraction * dx, point.y - start.y - fraction * dy),
  };
}

/** Explicit route approximation, never applied by the caller without user consent.
 * Projection is used only to select candidate vertices and nearby comparison points.
 * The reported bound is computed with WGS84 geodesic distances and a triangle-
 * inequality sampling allowance, not with the approximate projected distances.
 */
export function simplifyCorridorPath(
  source: readonly Position[],
  maximumDeviationM: number,
): CorridorSimplification {
  if (source.length < 2 || source.length > 10000)
    throw new Error('Route simplification accepts 2–10,000 points.');
  if (!Number.isFinite(maximumDeviationM) || maximumDeviationM < 50 || maximumDeviationM > 5000)
    throw new Error('Choose an allowed deviation from 50 to 5,000 metres.');
  const points = source
    .map((point) => measurementPoint(...point))
    .filter((point, index, all) => {
      const previous = all[index - 1];
      return previous?.[0] !== point[0] || previous[1] !== point[1];
    });
  if (points.length < 2) throw new Error('Choose a route with distinct endpoints.');
  if (points.some((point) => Math.abs(point[1]) > 80))
    throw new Error('Route simplification is limited to 80°S–80°N.');
  const originals = points.slice(1).map((end, index) => {
    const start = pointAt(points, index);
    if (Math.abs(end[0] - start[0]) > 180)
      throw new Error('Split routes crossing 180° longitude before creating a corridor.');
    return Geodesic.WGS84.InverseLine(start[1], start[0], end[1], end[0]);
  });
  const lengthM = originals.reduce((total, line) => total + line.s13, 0);
  if (!Number.isFinite(lengthM) || lengthM > 200000 || lengthM < 1)
    throw new Error('Route simplification requires a path from 1 metre to 200 km.');
  const centreLat = points.reduce((sum, point) => sum + point[1], 0) / points.length;
  const cos = Math.cos((centreLat * Math.PI) / 180),
    scale = (Math.PI * 6371008.8) / 180;
  const project = (point: Position): PlanePoint => ({
    x: point[0] * cos * scale,
    y: point[1] * scale,
  });
  const projected = points.map(project);
  const at = (index: number) => {
    const value = projected[index];
    if (!value) throw new Error('Route projection is incomplete.');
    return value;
  };
  const segment = (start: number, end: number) => {
    let index = -1,
      deviation = 0;
    for (let i = start + 1; i < end; i++) {
      const distance = onSegment(at(i), at(start), at(end)).distance;
      if (distance > deviation) {
        index = i;
        deviation = distance;
      }
    }
    return { start, end, index, deviation };
  };
  const segments = [segment(0, points.length - 1)];
  while (segments.length < 31) {
    const worst = segments.reduce((best, value) =>
      value.deviation > best.deviation ? value : best,
    );
    if (worst.index < 0 || worst.deviation < 0.01) break;
    segments.splice(
      segments.indexOf(worst),
      1,
      segment(worst.start, worst.index),
      segment(worst.index, worst.end),
    );
  }
  segments.sort((a, b) => a.start - b.start);
  const simplified = [pointAt(points, 0), ...segments.map((value) => pointAt(points, value.end))];
  const comparisons = simplified.slice(1).map((end, index) => {
    const start = pointAt(simplified, index);
    return {
      start: project(start),
      end: project(end),
      line: Geodesic.WGS84.InverseLine(start[1], start[0], end[1], end[0]),
    };
  });
  let maximumDistanceM = 0,
    maximumSpacingM = 0;
  for (const [lineIndex, line] of originals.entries()) {
    // <=12,000 samples for a <=200 km route with <=10,000 vertices.
    const steps = Math.max(1, Math.ceil(line.s13 / 100));
    maximumSpacingM = Math.max(maximumSpacingM, line.s13 / steps);
    for (let step = lineIndex === 0 ? 0 : 1; step <= steps; step++) {
      const sample = line.Position((line.s13 * step) / steps);
      const point = measurementPoint(sample.lon2 ?? NaN, sample.lat2 ?? NaN);
      const planar = project(point);
      let nearest = comparisons[0];
      if (!nearest) throw new Error('The simplified path is incomplete.');
      let chosen = onSegment(planar, nearest.start, nearest.end);
      for (const candidate of comparisons.slice(1)) {
        const distance = onSegment(planar, candidate.start, candidate.end);
        if (distance.distance < chosen.distance) {
          nearest = candidate;
          chosen = distance;
        }
      }
      const target = nearest.line.Position(nearest.line.s13 * chosen.fraction);
      const separation =
        Geodesic.WGS84.Inverse(point[1], point[0], target.lat2 ?? NaN, target.lon2 ?? NaN).s12 ??
        NaN;
      if (!Number.isFinite(separation)) throw new Error('Could not verify route approximation.');
      maximumDistanceM = Math.max(maximumDistanceM, separation);
    }
  }
  // Each original point is within half a sample interval of a checked sample.
  // Distance to the comparison curve is 1-Lipschitz under geodesic distance.
  const deviationBoundM = Math.ceil(maximumDistanceM + maximumSpacingM / 2 + 0.1);
  if (deviationBoundM > maximumDeviationM)
    throw new Error(
      `The 32-point approximation can deviate by up to ${deviationBoundM} m. Increase the allowed deviation or choose a shorter route.`,
    );
  return {
    points: simplified,
    originalCount: source.length,
    lengthKm: lengthM / 1000,
    deviationBoundM,
  };
}
