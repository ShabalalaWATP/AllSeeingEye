import { fetchTerrainElevations } from '@/lib/api/terrain';
import type { RfAnalysis } from './rfAnalysis';
import type { RfInputs } from './rfPlanning';
import type { RfEngineeringSettings } from './rfEngineering';
import type { RfTerrainSamplePlan } from './rfTerrainTypes';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { createAutomaticTerrainPlan, rfRefinementRadius } from './rfAutomation';
import type { RfElevationCache } from './rfElevationCache';
import { mergeRfTerrainSamples } from './rfTerrainMerge';

type TerrainStudy = Extract<RfAnalysis, { kind: 'terrain' }>;
interface StudyRequest {
  input: RfInputs;
  engineering: RfEngineeringSettings;
  plan: RfTerrainSamplePlan;
  refine: boolean;
  cache: RfElevationCache;
  signal: AbortSignal;
  onProgress: (progress: string) => void;
}
const REFINEMENT_WARNING =
  'Automatic refinement was unavailable. The first completed terrain screen is shown. ' +
  'Retry or choose a manual survey radius to examine another area.';

/** At most two bounded study passes. Partial or cancelled work is never cached or published. */
export async function runRfTerrainStudy(request: StudyRequest): Promise<TerrainStudy> {
  const { input, engineering, cache, signal, onProgress } = request;
  const calculate = async (plan: RfTerrainSamplePlan, refining: boolean): Promise<TerrainStudy> => {
    signal.throwIfAborted();
    let elevations = cache.get(plan.positions);
    onProgress(
      elevations
        ? 'Reusing sampled terrain'
        : refining
          ? 'Refining estimated coverage'
          : 'Sampling terrain',
    );
    if (!elevations) {
      elevations = await fetchTerrainElevations(plan.positions, signal);
      signal.throwIfAborted();
      cache.put(plan.positions, elevations);
    }
    signal.throwIfAborted();
    return {
      kind: 'terrain',
      input,
      plan,
      elevations,
      terrain: analyseRfTerrain(input, plan, elevations.elevations_m, engineering),
    };
  };
  const initial = await calculate(request.plan, false);
  signal.throwIfAborted();
  if (!request.refine || request.plan.kind !== 'radial') return initial;
  try {
    const radius = rfRefinementRadius(initial.terrain);
    if (radius === null) return initial;
    const plan = createAutomaticTerrainPlan(request.plan.origin, radius);
    if (
      (radius > request.plan.maxDistanceKm && plan.maxDistanceKm <= request.plan.maxDistanceKm) ||
      JSON.stringify(plan.positions) === JSON.stringify(request.plan.positions)
    )
      throw new Error('Refinement has no additional supported terrain.');
    const refined = await calculate(plan, true);
    signal.throwIfAborted();
    const merged = mergeRfTerrainSamples(initial, refined);
    const terrain = analyseRfTerrain(
      input,
      merged.plan,
      merged.elevations.elevations_m,
      engineering,
    );
    return {
      ...refined,
      ...merged,
      terrain: {
        ...terrain,
        warnings: [
          ...terrain.warnings,
          `Automatic area study checked ${initial.plan.maxDistanceKm.toFixed(1)} km, then refined once to ${refined.plan.maxDistanceKm.toFixed(1)} km. ${terrain.sampleCount} samples from both passes were retained inside the final radius. No further passes were requested.`,
        ],
      },
    };
  } catch {
    signal.throwIfAborted();
    return {
      ...initial,
      terrain: { ...initial.terrain, warnings: [...initial.terrain.warnings, REFINEMENT_WARNING] },
    };
  }
}
