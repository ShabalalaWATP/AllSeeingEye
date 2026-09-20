import { expect, it } from 'vitest';
import { createRfDraft } from './rfDraft';
import { parseRfStudy, readRfStudy, snapshotRfStudy, studyInputDifferences } from './rfStudy';
import { createRfTerrainPath } from './rfTerrainSampling';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
const names = { origin: 'Hill', receiver: 'Village' };
const snapshot = () => snapshotRfStudy(createRfDraft(), [0, 0], [0.1, 0], names, null);
it('round-trips an independent validated snapshot without retaining mutable draft references', () => {
  const draft = createRfDraft();
  const value = snapshotRfStudy(draft, [0, 0], [0.1, 0], names, null);
  draft.values.frequencyMHz = '400';
  names.origin = 'Changed';
  expect(value.draft.values.frequencyMHz).toBe('900');
  expect(value.siteNames.origin).toBe('Hill');
  expect(readRfStudy(JSON.stringify(value))).toEqual(value);
  expect(studyInputDifferences(value, draft)).toContain('Frequency (MHz)');
});
it('rejects unsupported versions, arbitrary payloads, non-finite numbers, invalid coordinates and remote references', () => {
  const value = snapshot();
  for (const bad of [
    { ...value, schemaVersion: 2 },
    { ...value, observations: [] },
    { ...value, origin: [181, 0] },
    { ...value, origin: [NaN, 0] },
    { ...value, provenance: { ...value.provenance, terrainSourceUrl: 'javascript:alert(1)' } },
    {
      ...value,
      draft: { ...value.draft, values: { ...value.draft.values, frequencyMHz: 'Infinity' } },
    },
  ])
    expect(() => parseRfStudy(bad)).toThrow();
  expect(() => readRfStudy(' '.repeat(128 * 1024 + 1))).toThrow(/128 KiB/);
});
it('saves free-space result values and source assumptions', () => {
  const value = snapshotRfStudy(
    { ...createRfDraft(), propagation: 'free-space', study: 'link' },
    [0, 0],
    [0.1, 0],
    names,
    null,
  );
  expect(value.result).toMatchObject({ kind: 'free-space', status: 'free-space reference' });
  expect(value.result?.receivedDbm).toBeTypeOf('number');
  expect(value.provenance.model).toContain('P.525');
});
it('retains ordered sampled terrain and profile spacing without treating imports as current map analysis', () => {
  const plan = createRfTerrainPath([0, 0], [0.02, 0], 5);
  const terrain = analyseRfTerrain(DEFAULT_RF_INPUTS, plan, [0, 0, 100, 0, 0]);
  const value = snapshotRfStudy(createRfDraft(), [0, 0], [0.02, 0], names, {
    kind: 'terrain',
    plan,
    terrain,
    input: DEFAULT_RF_INPUTS,
    elevations: {
      elevations_m: [0, 0, 100, 0, 0],
      zoom: 10,
      resolution_m: 150,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Test DEM',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Coarse samples.',
    },
  });
  expect(value.terrainEvidence?.samples[2]?.[2]).toBe(100);
  expect(value.terrainEvidence?.profiles[0]?.indices).toEqual(plan.profiles[0]?.indices);
  expect(value.result?.sampleCount).toBe(5);
  expect(value.provenance.terrainAttribution).toBe('Test DEM');
  const broken = structuredClone(value);
  broken.terrainEvidence!.profiles[0]!.indices[0] = 999;
  expect(() => parseRfStudy(broken)).toThrow();
});
