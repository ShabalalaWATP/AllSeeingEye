import type { RfAnalysis } from './rfAnalysis';
import { RF_PHYSICAL_REFERENCE } from './rfEngineering';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import type { RfTerrainStatus } from './rfTerrainTypes';

export type RfLinkAdvice =
  | { kind: 'budget'; shortfallDb: number }
  | {
      kind: 'height';
      site: 'transmitter' | 'receiver';
      heightM: number;
      addedM: number;
      planningMarginDb: number;
      status: RfTerrainStatus;
    };

/** A local what-if using the same DEM. It neither changes equipment inputs nor requests data. */
export function rfLinkAdvice(
  analysis: Extract<RfAnalysis, { kind: 'terrain' }>,
): RfLinkAdvice | null {
  const { terrain, input } = analysis;
  const profile = terrain.path;
  if (
    !profile ||
    profile.status === 'unknown' ||
    profile.minimumFresnelClearanceM === null ||
    terrain.belowSeaLevelSamples > 0
  )
    return null;
  const margin = profile.planningMarginDb ?? profile.marginDb;
  if (profile.minimumFresnelClearanceM >= 0)
    return margin !== null && margin < 0 ? { kind: 'budget', shortfallDb: -margin } : null;
  const distance = profile.distanceKm * 1000;
  const interior = profile.points.slice(1, -1);
  const candidates = (['transmitter', 'receiver'] as const).flatMap((site) => {
    let extra = 0;
    for (const point of interior) {
      if (point.fresnelClearanceM === null) return [];
      const fraction = point.distanceM / distance;
      const weight = site === 'transmitter' ? 1 - fraction : fraction;
      extra = Math.max(extra, -point.fresnelClearanceM / weight);
    }
    const key = site === 'transmitter' ? 'transmitHeightM' : 'receiveHeightM';
    // Round upward with a one-metre allowance for the sampled screen, not a DEM accuracy claim.
    const heightM = Math.ceil(input[key] + extra + 1);
    if (!Number.isFinite(heightM) || heightM > 10_000) return [];
    const trial = evaluateRfTerrainProfile(
      { ...input, [key]: heightM },
      profile.points.map((point) => point.position),
      profile.points.map((point) => point.distanceM),
      profile.points.map((point) => point.elevationM),
      terrain.engineering ?? { ...RF_PHYSICAL_REFERENCE, reserveDb: profile.reserveDb ?? 0 },
    );
    if (
      trial.planningMarginDb == null ||
      trial.minimumFresnelClearanceM === null ||
      trial.minimumFresnelClearanceM < 0
    )
      return [];
    return [
      {
        kind: 'height' as const,
        site,
        heightM,
        addedM: heightM - input[key],
        planningMarginDb: trial.planningMarginDb,
        status: trial.status,
      },
    ];
  });
  return candidates.sort((a, b) => a.addedM - b.addedM)[0] ?? null;
}
