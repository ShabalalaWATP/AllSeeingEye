import { expect, it } from 'vitest';
import fixture from '@/test/fixtures/mapWorkspaceRadio.json';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { createRfTerrainPath } from '@/lib/map/rfTerrainSampling';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';

it('keeps actual terrain snapshots compatible with the backend contract fixture', () => {
  const origin: [number, number] = [0, 0];
  const receiver: [number, number] = [-0.02, 0];
  const plan = createRfTerrainPath(origin, receiver, 5);
  const elevations = [0, 0, 100, 0, 0];
  const terrain = analyseRfTerrain(DEFAULT_RF_INPUTS, plan, elevations);
  const value = snapshotRfStudy(
    createRfDraft(),
    origin,
    receiver,
    { origin: 'Hill', receiver: 'Village' },
    {
      kind: 'terrain',
      plan,
      terrain,
      input: DEFAULT_RF_INPUTS,
      elevations: {
        elevations_m: elevations,
        zoom: 10,
        resolution_m: 150,
        provider: 'Mapzen Terrain Tiles',
        attribution: 'Synthetic contract fixture DEM',
        attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
        limitations: 'Synthetic test samples.',
      },
    },
  );
  value.savedAt = '2026-09-20T00:00:00.000Z';
  expect(value).toEqual(fixture);
});
