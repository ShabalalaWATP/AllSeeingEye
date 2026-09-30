import { expect, it } from 'vitest';
import { analyseTerrainStudy, planTerrainStudy, type TerrainStudyInput } from './terrainAnalysis';
import { terrainAnalysisLayers } from './terrainAnalysisLayers';
import { createRfTerrainPath } from './rfTerrainSampling';
import type { TerrainElevations } from '@/lib/api/terrain';
import type { PathLayer } from '@deck.gl/layers';

const input: TerrainStudyInput = {
  mode: 'profile',
  origin: [179.8, 0],
  end: [-179.8, 0],
  radiusKm: 1,
  observerHeightM: 2,
};
const provenance = (elevations_m: number[]): TerrainElevations => ({
  elevations_m,
  zoom: 10,
  resolution_m: 90,
  provider: 'Mapzen Terrain Tiles',
  attribution: 'Fixture terrain',
  attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
  limitations: 'Fixture only',
});

it('retains unknown extrema when no profile heights are known', () => {
  const plan = createRfTerrainPath(input.origin, input.end!, 3);
  const result = analyseTerrainStudy(input, plan, provenance([NaN, NaN, NaN]));
  expect(result.minimumM).toBeNull();
  expect(result.maximumM).toBeNull();
  expect(result.samples.every((sample) => sample.elevationM === null)).toBe(true);
  expect(result.warnings.join(' ')).toContain('never replaced with flat ground');
});

it('splits antimeridian profile lines instead of drawing across the flat map', () => {
  const plan = createRfTerrainPath(input.origin, input.end!, 5);
  const result = analyseTerrainStudy(input, plan, provenance([10, 20, 30, 40, 50]));
  const layer = terrainAnalysisLayers(result, true)[0] as PathLayer;
  const paths = layer.props.data as { position: [number, number] }[][];
  expect(paths).toHaveLength(2);
  for (const path of paths)
    expect(
      path.every(
        (sample, index) =>
          index === 0 || Math.abs(sample.position[0] - path[index - 1]!.position[0]) <= 180,
      ),
    ).toBe(true);
});

it.each(['missing-index', 'missing-distance', 'non-finite-distance', 'zero-distance'] as const)(
  'rejects a malformed terrain sample plan (%s) rather than reporting visible ground',
  (kind) => {
    const plan = createRfTerrainPath(input.origin, input.end!, 3);
    const profile = plan.profiles[0]!;
    if (kind === 'missing-index') profile.indices[1] = 99;
    if (kind === 'missing-distance') profile.distancesM = [];
    if (kind === 'non-finite-distance') profile.distancesM[1] = NaN;
    if (kind === 'zero-distance') profile.distancesM[1] = 0;
    expect(() => analyseTerrainStudy(input, plan, provenance([10, 20, 30]))).toThrow(
      'The terrain sample plan is invalid.',
    );
  },
);

it('rejects observer heights above the supported maximum', () => {
  expect(() => planTerrainStudy({ ...input, mode: 'visibility', observerHeightM: 501 })).toThrow(
    /500 metres/,
  );
});
