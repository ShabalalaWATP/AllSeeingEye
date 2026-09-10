import type { RfDraft, RfPropagation } from './rfDraft';
import { RF_ENVIRONMENT_DEFAULTS } from './rfDraft';
import { calculateRf, type RfInputs } from './rfPlanning';
import { parseRfEngineering } from './rfEngineering';
import { RF_PRESETS } from './rfPresets';
import type { RfTerrainAnalysis } from './rfTerrainTypes';
import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';
import { createRfTerrainRadials } from './rfTerrainSampling';

const RADII_KM = [1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50];
const roundRadius = (radius: number) => RADII_KM.find((value) => value >= radius) ?? 50;

/** Choose a supported model, without inferring live ionospheric or ground conditions. */
export function resolveRfMode(draft: RfDraft): RfPropagation {
  if (draft.propagation !== 'automatic') return draft.propagation ?? 'terrain';
  const frequency = Number(draft.values.frequencyMHz);
  if (frequency >= 30 || !Number.isFinite(frequency)) return 'terrain';
  if (draft.automaticHfMode) return draft.automaticHfMode;
  const preset = RF_PRESETS.find((item) => item.id === draft.presetId);
  return preset?.propagation === 'hf-skywave' ? 'hf-skywave' : 'hf-groundwave';
}

/** An initial search extent, not a propagation prediction or confirmed range limit. */
export function rfStudyRadius(input: RfInputs, draft: RfDraft): number {
  const mode = resolveRfMode(draft);
  if (mode !== 'terrain' && mode !== 'hf-groundwave')
    throw new Error('This model does not use a terrain or groundwave study radius.');
  if (draft.radiusMode !== 'automatic') {
    const raw = draft.environment?.radiusKm ?? RF_ENVIRONMENT_DEFAULTS.radiusKm;
    const value = raw.trim() ? Number(raw) : NaN;
    const min = mode === 'terrain' ? 1 : 2;
    const max = mode === 'terrain' ? 50 : 200;
    if (!Number.isFinite(value) || value < min || value > max)
      throw new Error(`Area to analyse: enter a distance from ${min} to ${max} km.`);
    return value;
  }
  // Groundwave is one bounded native curve, so inspect its whole supported domain.
  if (mode === 'hf-groundwave') return 200;
  const reference = calculateRf(
    { ...input, distanceKm: 1 },
    parseRfEngineering(draft.engineering, mode),
  );
  // Give the ideal reference 25% search headroom. DEM elevations are still unknown here.
  return roundRadius(
    Math.max(1, Math.min(50, reference.horizonKm * 1.25, reference.sensitivityDistanceKm * 1.25)),
  );
}

/** Recommend at most one extra area pass. Unknown/water-surface evidence never drives expansion. */
export function rfRefinementRadius(terrain: RfTerrainAnalysis): number | null {
  const radius = terrain.maxDistanceKm;
  if (
    terrain.kind !== 'radial' ||
    terrain.radials.length === 0 ||
    !Number.isFinite(radius) ||
    radius < 1 ||
    radius > 50 ||
    terrain.missingSamples > 0 ||
    terrain.belowSeaLevelSamples > 0 ||
    terrain.radials.some((radial) => radial.status === 'unknown')
  )
    return null;
  const furthest = Math.max(...terrain.radials.map((radial) => radial.clearDistanceKm));
  if (furthest >= radius * 0.995) {
    const expanded = Math.min(50, radius * 2);
    return expanded > radius ? expanded : null;
  }
  if (furthest > radius * 0.2 || radius <= 1) return null;
  const firstTargets = terrain.radials.map((radial) => radial.samples[0]?.distanceKm ?? radius);
  const closer = roundRadius(
    Math.max(1, Math.min(radius / 2, Math.max(furthest * 2, Math.min(...firstTargets) * 2))),
  );
  return closer < radius ? closer : null;
}

/** Fit automatic studies inside the existing tile/latitude budget before any network request. */
export function createAutomaticTerrainPlan(origin: Position, radiusKm: number) {
  measurementPoint(...origin);
  if (Math.abs(origin[1]) > 85.05112878)
    throw new Error('Terrain sampling is unavailable beyond Web Mercator latitude coverage.');
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 50)
    throw new Error('Automatic terrain radius must be from 1 to 50 km.');
  let radius = radiusKm;
  // At most seven small, local plans (50, 25, ..., 1 km); no provider retries.
  for (let attempt = 0; attempt < 7; attempt++) {
    try {
      return createRfTerrainRadials(origin, radius);
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (
        radius <= 1 ||
        (!message.includes('64 tiles') && !message.includes('Web Mercator latitude'))
      )
        throw error;
      radius = Math.max(1, radius / 2);
    }
  }
  throw new Error('No supported terrain area could be planned at this location.');
}
