import type { TerrainElevations } from '@/lib/api/terrain';
import type { Position } from './geoJsonTypes';
import { createRfTerrainPath, createRfTerrainRadials } from './rfTerrainSampling';
import type { RfTerrainSamplePlan } from './rfTerrainTypes';

export interface TerrainStudyInput {
  mode: 'profile' | 'visibility';
  origin: Position;
  end?: Position;
  radiusKm: number;
  observerHeightM: number;
}
export interface TerrainStudySample {
  position: Position;
  distanceM: number;
  elevationM: number | null;
  visibility: 'visible' | 'hidden' | 'unknown' | 'observer';
}
export interface TerrainStudy {
  input: TerrainStudyInput;
  samples: TerrainStudySample[];
  provenance: TerrainElevations;
  minimumM: number | null;
  maximumM: number | null;
  warnings: string[];
}

/** Reuse the bounded geodesic sample planner, not the radio propagation model. */
export function planTerrainStudy(input: TerrainStudyInput): RfTerrainSamplePlan {
  if (
    !Number.isFinite(input.observerHeightM) ||
    input.observerHeightM < 0.5 ||
    input.observerHeightM > 500
  )
    throw new Error('Observer height must be from 0.5 to 500 metres above the ground.');
  if (input.mode === 'profile') {
    if (!input.end) throw new Error('Choose both endpoints for the terrain profile.');
    return createRfTerrainPath(input.origin, input.end);
  }
  return createRfTerrainRadials(input.origin, input.radiusKm);
}

const EARTH_RADIUS_M = 6371008.8;

/** Sampled geometric ground visibility, with spherical curvature and no refraction.
 * Each further sample is assessed independently: a higher hillside can reappear.
 * An unknown intermediate elevation invalidates later visibility on that ray.
 */
export function analyseTerrainStudy(
  input: TerrainStudyInput,
  plan: RfTerrainSamplePlan,
  source: TerrainElevations,
): TerrainStudy {
  if (source.elevations_m.length !== plan.positions.length)
    throw new Error('The terrain provider returned an incomplete sample set.');
  const elevations = source.elevations_m.map((height) => (Number.isFinite(height) ? height : null));
  const samples: TerrainStudySample[] = plan.positions.map((position, index) => ({
    position,
    distanceM: 0,
    elevationM: elevations[index] ?? null,
    visibility: index === 0 ? 'observer' : 'unknown',
  }));
  const originM = elevations[0];
  for (const profile of plan.profiles) {
    let horizon = -Infinity;
    let unknown = originM == null || originM < 0;
    for (const [offset, index] of profile.indices.entries()) {
      if (offset === 0) continue;
      const sample = samples[index];
      const distanceM = profile.distancesM[offset];
      if (!sample || distanceM === undefined || !Number.isFinite(distanceM) || distanceM <= 0)
        throw new Error('The terrain sample plan is invalid.');
      sample.distanceM = distanceM;
      if (sample.elevationM === null || sample.elevationM < 0) unknown = true;
      if (input.mode !== 'visibility' || unknown || originM == null || sample.elevationM === null)
        continue;
      const angle = Math.atan2(
        sample.elevationM - originM - input.observerHeightM - distanceM ** 2 / (2 * EARTH_RADIUS_M),
        distanceM,
      );
      sample.visibility = angle >= horizon ? 'visible' : 'hidden';
      horizon = Math.max(horizon, angle);
    }
  }
  const known = elevations.filter((height): height is number => height !== null);
  const warnings = [
    'Source terrain is sampled at zoom 10. More samples do not improve the source elevation accuracy.',
  ];
  if (known.some((height) => height < 0))
    warnings.push(
      'Negative source elevations may represent land below sea level or bathymetry. Visibility beyond them is unknown; water surfaces are not inferred.',
    );
  if (known.length !== elevations.length)
    warnings.push('Missing elevations remain unknown and are never replaced with flat ground.');
  if (input.mode === 'visibility')
    warnings.push(
      'Only the marked ground samples are assessed, along 24 directions. Gaps, buildings, vegetation and atmospheric refraction are not modelled. This is not a radio coverage prediction.',
    );
  return {
    input,
    samples,
    provenance: source,
    minimumM: known.length ? Math.min(...known) : null,
    maximumM: known.length ? Math.max(...known) : null,
    warnings,
  };
}
