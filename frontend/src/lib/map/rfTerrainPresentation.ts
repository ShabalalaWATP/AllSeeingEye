import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import type {
  RfTerrainAnalysis,
  RfTerrainProfile,
  RfTerrainProfilePoint,
  RfTerrainStatus,
} from './rfTerrainTypes';

/** Shared by the map, profile and text legend. Text and symbols also identify each state. */
export const RF_STATUS_COLOURS: Record<RfTerrainStatus, [number, number, number, number]> = {
  clear: [45, 235, 195, 255],
  risk: [255, 194, 71, 255],
  blocked: [255, 69, 103, 255],
  unknown: [154, 167, 188, 230],
};
export const RF_STATUS_CSS: Record<RfTerrainStatus, string> = {
  clear: '#2debc3',
  risk: '#ffc247',
  blocked: '#ff4567',
  unknown: '#9aa7bc',
};

/** First sampled intrusions into this TX–RX ray, not range estimates for other receivers. */
export function rfPathSummary(profile: RfTerrainProfile): {
  firstBlocked: RfTerrainProfilePoint | null;
  firstRisk: RfTerrainProfilePoint | null;
} {
  const interior = profile.status === 'unknown' ? [] : profile.points.slice(1, -1);
  return {
    firstBlocked:
      interior.find((point) => point.clearanceM !== null && point.clearanceM <= 0) ?? null,
    firstRisk:
      interior.find((point) => point.fresnelClearanceM !== null && point.fresnelClearanceM < 0) ??
      null,
  };
}

/** Keep the direct ray obstructed after a ridge, even where later local clearance improves. */
export function rfPathPointStatus(
  profile: RfTerrainProfile,
  point: RfTerrainProfilePoint,
  summary = rfPathSummary(profile),
): RfTerrainStatus {
  if (profile.status === 'unknown' || point.clearanceM === null) return 'unknown';
  if (summary.firstBlocked && point.distanceM >= summary.firstBlocked.distanceM) return 'blocked';
  if (
    (summary.firstRisk && point.distanceM >= summary.firstRisk.distanceM) ||
    (profile.marginDb !== null && profile.marginDb < 0)
  )
    return 'risk';
  return 'clear';
}

/** The interval immediately before a sampled intrusion has no resolved crossing location. */
export function rfPathSegmentStatus(
  profile: RfTerrainProfile,
  start: RfTerrainProfilePoint,
  end: RfTerrainProfilePoint,
  summary = rfPathSummary(profile),
): RfTerrainStatus {
  const status = rfPathPointStatus(profile, start, summary);
  if (
    status === 'clear' &&
    ((summary.firstBlocked && end.distanceM >= summary.firstBlocked.distanceM) ||
      (summary.firstRisk && end.distanceM >= summary.firstRisk.distanceM))
  )
    return 'risk';
  return status;
}

export function rfDestination(origin: Position, bearing: number, distanceKm: number): Position {
  const point = Geodesic.WGS84.Direct(origin[1], origin[0], bearing, distanceKm * 1000);
  return [point.lon2 ?? origin[0], point.lat2 ?? origin[1]];
}

export function rfContinuousRing(ring: Position[]): Position[] {
  return ring.reduce<Position[]>((points, [lon, lat]) => {
    const previous = points.at(-1);
    points.push([
      previous ? previous[0] + (((((lon - previous[0] + 180) % 360) + 360) % 360) - 180) : lon,
      lat,
    ]);
    return points;
  }, []);
}

/** Decorative interpolation is limited to the shorter passing radius of adjacent bearings.
 * Unknown bearings and bearings with no passing target leave a gap. No terrain is inferred.
 */
export function rfInterpolatedFootprint(analysis: RfTerrainAnalysis): Position[][] {
  if (analysis.kind !== 'radial' || analysis.radials.length < 4) return [];
  const radials = [...analysis.radials].sort((a, b) => a.bearingDegrees - b.bearingDegrees);
  return radials.flatMap((radial, index) => {
    const next = radials[(index + 1) % radials.length] ?? radial;
    const distance = Math.min(radial.clearDistanceKm, next.clearDistanceKm);
    if (distance <= 0 || radial.status === 'unknown' || next.status === 'unknown') return [];
    const span = (next.bearingDegrees - radial.bearingDegrees + 360) % 360;
    if (span <= 0 || span > 90) return [];
    const arc = Array.from({ length: 7 }, (_, step) =>
      rfDestination(analysis.origin, radial.bearingDegrees + (span * step) / 6, distance),
    );
    return [rfContinuousRing([analysis.origin, ...arc, analysis.origin])];
  });
}
