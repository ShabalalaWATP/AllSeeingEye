import { describe, expect, it } from 'vitest';
import { analyseTerrainStudy, planTerrainStudy, type TerrainStudyInput } from './terrainAnalysis';
import { createRfTerrainPath, createRfTerrainRadials } from './rfTerrainSampling';
import { terrainAnalysisLayers } from './terrainAnalysisLayers';
import type { TerrainElevations } from '@/lib/api/terrain';

const input: TerrainStudyInput = {
  mode: 'visibility',
  origin: [0, 51],
  radiusKm: 1,
  observerHeightM: 2,
};
function source(elevations: number[]): TerrainElevations {
  return {
    elevations_m: elevations,
    zoom: 10,
    resolution_m: 90,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Fixture terrain',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: 'Fixture only',
  };
}

describe('bounded standalone terrain studies', () => {
  it('bounds radial work and validates sites and heights before requesting data', () => {
    expect(planTerrainStudy(input).positions).toHaveLength(409);
    expect(() => planTerrainStudy({ ...input, radiusKm: 51 })).toThrow(/50/);
    expect(() => planTerrainStudy({ ...input, observerHeightM: NaN })).toThrow(/height/);
    expect(() => planTerrainStudy({ ...input, observerHeightM: 0 })).toThrow(/height/);
    expect(() => planTerrainStudy({ ...input, origin: [0, 89] })).toThrow(/coverage/);
    expect(() => planTerrainStudy({ ...input, mode: 'profile' })).toThrow(/endpoints/);
    expect(() => planTerrainStudy({ ...input, mode: 'profile', end: [10, 51] })).toThrow(/200 km/);
  });

  it('assesses every ground target, including a higher ridge beyond a hidden valley', () => {
    const plan = createRfTerrainRadials(input.origin, 1, 4, 4);
    const elevations = plan.positions.map(() => 100);
    // A 20m ridge hides the low valley, but not the final high hillside.
    elevations[1] = 120;
    elevations[2] = 100;
    elevations[3] = 100;
    elevations[4] = 700;
    const result = analyseTerrainStudy(input, plan, source(elevations));
    expect(result.samples.slice(1, 5).map((sample) => sample.visibility)).toEqual([
      'visible',
      'hidden',
      'hidden',
      'visible',
    ]);
    expect(result.warnings.join(' ')).toContain('not a radio coverage prediction');
  });

  it('treats missing/bathymetric intermediates as unknown for the remainder of that ray', () => {
    const plan = createRfTerrainRadials(input.origin, 1, 4, 4);
    const elevations = plan.positions.map(() => 100);
    elevations[2] = Number.NaN;
    elevations[6] = -1;
    const result = analyseTerrainStudy(input, plan, source(elevations));
    expect(result.samples[1]?.visibility).toBe('visible');
    expect(result.samples.slice(2, 5).every((sample) => sample.visibility === 'unknown')).toBe(
      true,
    );
    expect(result.samples.slice(6, 9).every((sample) => sample.visibility === 'unknown')).toBe(
      true,
    );
    expect(result.samples[2]?.elevationM).toBeNull();
    expect(result.minimumM).toBe(-1);
    expect(result.warnings.join(' ')).toMatch(/bathymetry.*Missing elevations/s);
    const layers = terrainAnalysisLayers(result, true);
    expect(layers.map((layer) => layer.id)).toEqual(['terrain-study-samples']);
  });

  it('preserves profile elevations and provenance, with no invented missing values', () => {
    const draft = { ...input, mode: 'profile' as const, end: [0.01, 51] as [number, number] };
    const plan = createRfTerrainPath(draft.origin, draft.end, 3);
    const result = analyseTerrainStudy(draft, plan, source([-1, NaN, 123]));
    expect(result.samples.map((sample) => sample.elevationM)).toEqual([-1, null, 123]);
    expect(result.maximumM).toBe(123);
    expect(result.provenance.attribution).toBe('Fixture terrain');
    expect(terrainAnalysisLayers(result, false, 2).map((layer) => layer.id)).toEqual([
      'terrain-study-profile',
      'terrain-study-samples',
      'terrain-study-highlight',
    ]);
    expect(() => analyseTerrainStudy(draft, plan, source([1]))).toThrow(/incomplete/);
    expect(terrainAnalysisLayers(null, false)).toEqual([]);
  });
});
