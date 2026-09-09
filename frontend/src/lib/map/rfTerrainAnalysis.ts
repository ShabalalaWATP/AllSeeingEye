import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import type { RfInputs } from './rfPlanning';
import type {
  RfTerrainAnalysis,
  RfTerrainRadial,
  RfTerrainRadialSample,
  RfTerrainSamplePlan,
} from './rfTerrainTypes';
export type { RfTerrainAnalysis, RfTerrainProfile, RfTerrainRadial } from './rfTerrainTypes';

export const RF_TERRAIN_LIMITATIONS = [
  'Coarse terrain samples can miss ridges, buildings, trees and local obstructions. Clear means only that the sampled screen passed, not reliable reception.',
  'Standard k=4/3 Earth curvature, 60% first Fresnel clearance and free-space loss plus one dominant sampled knife edge. This is not a full ITU-R P.526, ITM or measured coverage model.',
  'No weather, clutter, interference, antenna pattern or fade margin. Ground elevations use the source DEM datum; antenna heights are above ground.',
];

/** Missing DEM never becomes zero terrain or a clear path. Negative values remain unaltered. */
export function analyseRfTerrain(
  input: RfInputs,
  plan: RfTerrainSamplePlan,
  elevationsM: readonly (number | null)[],
): RfTerrainAnalysis {
  if (
    plan.positions.length > 409 ||
    plan.positions.length < 3 ||
    elevationsM.length !== plan.positions.length ||
    plan.profiles.length < 1 ||
    plan.profiles.length > 24 ||
    (plan.kind === 'path' && plan.profiles.length !== 1)
  )
    throw new Error('Terrain sample results do not match the bounded sample plan.');
  for (const profile of plan.profiles) {
    if (
      profile.indices.length > 129 ||
      profile.indices.length < 3 ||
      profile.indices.length !== profile.distancesM.length ||
      profile.indices.some(
        (index) => !Number.isInteger(index) || index < 0 || index >= plan.positions.length,
      )
    )
      throw new Error('Invalid terrain sample profile.');
  }
  const values = elevationsM.map((value) =>
    value !== null && Number.isFinite(value) ? value : null,
  );
  const missingSamples = values.filter((value) => value === null).length;
  const belowSeaLevelSamples = values.filter((value) => value !== null && value < 0).length;
  const warnings = [...RF_TERRAIN_LIMITATIONS];
  if (missingSamples)
    warnings.push(
      `${missingSamples} terrain samples are missing. Affected paths are unknown, not clear.`,
    );
  if (belowSeaLevelSamples)
    warnings.push(
      'Negative elevations are retained. Mapzen includes bathymetry as well as land below sea level. Water surfaces have not been identified: verify these paths before interpreting the result.',
    );
  const evaluate = (
    profile: RfTerrainSamplePlan['profiles'][number],
    length = profile.indices.length,
  ) => {
    const indices = profile.indices.slice(0, length);
    return evaluateRfTerrainProfile(
      input,
      indices.map((index) => plan.positions[index] ?? plan.origin),
      profile.distancesM.slice(0, length),
      indices.map((index) => values[index] ?? null),
    );
  };
  const first = plan.profiles[0];
  if (!first) throw new Error('Missing terrain profile.');
  const radials: RfTerrainRadial[] =
    plan.kind === 'radial'
      ? plan.profiles.map((profile) => {
          const samples: RfTerrainRadialSample[] = [];
          let clearDistanceKm = 0,
            stopDistanceKm: number | null = null;
          let status: RfTerrainRadial['status'] = 'clear';
          // The first assessed target has one actual interior DEM point. Later targets
          // reuse their prefix profile; never extrapolate beyond the first failing sample.
          for (let length = 3; length <= profile.indices.length; length++) {
            const assessment = evaluate(profile, length);
            const position = plan.positions[profile.indices[length - 1] ?? 0] ?? plan.origin;
            samples.push({
              position,
              distanceKm: assessment.distanceKm,
              status: assessment.status,
              marginDb: assessment.marginDb,
            });
            if (assessment.status !== 'clear') {
              status = assessment.status;
              stopDistanceKm = assessment.distanceKm;
              break;
            }
            clearDistanceKm = assessment.distanceKm;
          }
          return {
            bearingDegrees: profile.bearingDegrees,
            clearDistanceKm,
            stopDistanceKm,
            status,
            samples,
          };
        })
      : [];
  if (plan.kind === 'radial')
    warnings.push(
      'Only sampled bearings are screened. Each bearing stops at its first obstruction, Fresnel restriction, negative link margin or missing sample. Areas between rays and beyond a stop have not been assessed.',
    );
  return {
    kind: plan.kind,
    origin: plan.origin,
    receiver: plan.receiver,
    maxDistanceKm: plan.maxDistanceKm,
    path: plan.kind === 'path' ? evaluate(first) : null,
    radials,
    warnings,
    sampleCount: values.length,
    missingSamples,
    belowSeaLevelSamples,
  };
}
