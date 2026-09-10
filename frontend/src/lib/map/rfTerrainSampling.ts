import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';
import type { RfTerrainSamplePlan } from './rfTerrainTypes';
export type { RfTerrainSamplePlan } from './rfTerrainTypes';

export const RF_TERRAIN_MAX_PATH_KM = 200;
export const RF_TERRAIN_MAX_RADIUS_KM = 50;
export const RF_TERRAIN_MAX_PATH_SAMPLES = 769;
/** Area studies retain their existing fixed request and rendering budget. */
export const RF_TERRAIN_MAX_SAMPLES = 409;
/** Two automatic area passes share one origin; only analysis can combine their samples. */
export const RF_TERRAIN_MAX_AREA_ANALYSIS_SAMPLES = RF_TERRAIN_MAX_SAMPLES * 2 - 1;

function count(value: number, minimum: number, maximum: number, label: string) {
  if (!Number.isInteger(value) || value < minimum || value > maximum)
    throw new Error(`${label} must be an integer from ${minimum} to ${maximum}.`);
}
function supported(position: Position): Position {
  const point = measurementPoint(...position);
  if (Math.abs(point[1]) > 85.05112878)
    throw new Error('Terrain sampling is unavailable beyond Web Mercator latitude coverage.');
  return point;
}
function destination(origin: Position, bearing: number, distanceM: number): Position {
  const point = Geodesic.WGS84.Direct(origin[1], origin[0], bearing, distanceM);
  return supported([point.lon2 ?? NaN, point.lat2 ?? NaN]);
}
function tileBudget(plan: RfTerrainSamplePlan): RfTerrainSamplePlan {
  const tiles = new Set(
    plan.positions.map(([lon, lat]) => {
      const x = Math.min(1023, Math.max(0, Math.floor(((lon + 180) / 360) * 1024)));
      const phi = (lat * Math.PI) / 180;
      const y = Math.min(
        1023,
        Math.max(0, Math.floor(((1 - Math.asinh(Math.tan(phi)) / Math.PI) / 2) * 1024)),
      );
      return `${x}:${y}`;
    }),
  );
  if (tiles.size > 64)
    throw new Error(
      'This terrain screen spans more than 64 tiles. Reduce the radius or choose a shorter path, especially at high latitudes.',
    );
  return plan;
}

/** Aim for 100 metre path intervals, capped to keep requests and rendering bounded.
 * Equal geodesic spacing does not imply that the source DEM resolves every interval.
 */
export function createRfTerrainPath(
  origin: Position,
  receiver: Position,
  samples?: number,
): RfTerrainSamplePlan {
  const start = supported(origin),
    end = supported(receiver);
  if (samples !== undefined) count(samples, 3, RF_TERRAIN_MAX_PATH_SAMPLES, 'Path samples');
  const inverse = Geodesic.WGS84.Inverse(start[1], start[0], end[1], end[0]);
  const distanceM = inverse.s12 ?? NaN;
  const bearing = inverse.azi1 ?? NaN;
  if (!Number.isFinite(distanceM) || distanceM < 1 || distanceM > RF_TERRAIN_MAX_PATH_KM * 1000)
    throw new Error('Terrain paths must be at least 1 metre and no more than 200 km.');
  const sampleCount =
    samples ?? Math.min(RF_TERRAIN_MAX_PATH_SAMPLES, Math.max(3, Math.ceil(distanceM / 100) + 1));
  const distancesM = Array.from(
    { length: sampleCount },
    (_, index) => (distanceM * index) / (sampleCount - 1),
  );
  const positions = distancesM.map((distance, index) =>
    index === 0 ? start : index === sampleCount - 1 ? end : destination(start, bearing, distance),
  );
  return tileBudget({
    kind: 'path',
    origin: start,
    receiver: end,
    maxDistanceKm: distanceM / 1000,
    positions,
    profiles: [
      {
        bearingDegrees: (bearing + 360) % 360,
        indices: positions.map((_, index) => index),
        distancesM,
      },
    ],
  });
}

/** One shared origin plus 24 × 17 DEM points, concentrated towards the transmitter.
 * Nearby sampling improves without increasing work. No smoothing between bearings.
 */
export function createRfTerrainRadials(
  origin: Position,
  radiusKm: number,
  bearings = 24,
  steps = 17,
): RfTerrainSamplePlan {
  const start = supported(origin);
  count(bearings, 4, 24, 'Radial bearings');
  count(steps, 2, 17, 'Radial steps');
  if (!Number.isFinite(radiusKm) || radiusKm < 0.01 || radiusKm > RF_TERRAIN_MAX_RADIUS_KM)
    throw new Error('Terrain radius must be from 0.01 to 50 km.');
  const positions: Position[] = [start];
  const profiles = Array.from({ length: bearings }, (_, index) => {
    const bearingDegrees = (index * 360) / bearings;
    const indices = [0],
      distancesM = [0];
    for (let step = 1; step <= steps; step++) {
      // A half-metre progression keeps the first assessed prefix (two steps) at
      // least one metre. With <=17 steps and >=10m radius the outer radius stays exact.
      const distanceM = Math.max(radiusKm * 1000 * (step / steps) ** 2, step / 2);
      indices.push(positions.length);
      distancesM.push(distanceM);
      positions.push(destination(start, bearingDegrees, distanceM));
    }
    return { bearingDegrees, indices, distancesM };
  });
  return tileBudget({
    kind: 'radial',
    origin: start,
    receiver: null,
    maxDistanceKm: radiusKm,
    positions,
    profiles,
  });
}
