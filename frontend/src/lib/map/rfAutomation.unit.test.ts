import { expect, it } from 'vitest';
import { createRfDraft } from './rfDraft';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { createRfTerrainRadials } from './rfTerrainSampling';
import {
  createAutomaticTerrainPlan,
  resolveRfMode,
  rfRefinementRadius,
  rfStudyRadius,
} from './rfAutomation';

it('chooses by frequency and honours explicit models and an HF skywave preset', () => {
  expect(resolveRfMode(createRfDraft())).toBe('terrain');
  const hf = createRfDraft({ ...DEFAULT_RF_INPUTS, frequencyMHz: 7 });
  expect(resolveRfMode(hf)).toBe('hf-groundwave');
  expect(resolveRfMode({ ...hf, presetId: 'bowman-prc325-nvis' })).toBe('hf-skywave');
  expect(resolveRfMode({ ...hf, propagation: 'free-space' })).toBe('free-space');
  expect(resolveRfMode({ ...hf, automaticHfMode: 'hf-skywave' })).toBe('hf-skywave');
  expect(
    resolveRfMode({ ...hf, presetId: 'bowman-prc325-nvis', automaticHfMode: 'hf-groundwave' }),
  ).toBe('hf-groundwave');
  expect(resolveRfMode({ ...createRfDraft(), automaticHfMode: 'hf-skywave' })).toBe('terrain');
  expect(resolveRfMode(createRfDraft({ ...DEFAULT_RF_INPUTS, frequencyMHz: 30 }))).toBe('terrain');
  expect(resolveRfMode(createRfDraft({ ...DEFAULT_RF_INPUTS, frequencyMHz: NaN }))).toBe('terrain');
});

it('derives a bounded search extent without treating a hidden manual edit as an input', () => {
  const draft = createRfDraft();
  draft.environment!.radiusKm = '';
  expect(rfStudyRadius(DEFAULT_RF_INPUTS, draft)).toBe(25);
  expect(rfStudyRadius({ ...DEFAULT_RF_INPUTS, transmitDbm: -100 }, draft)).toBe(1);
  expect(
    rfStudyRadius(
      { ...DEFAULT_RF_INPUTS, transmitHeightM: 1000, receiveHeightM: 1000, transmitDbm: 60 },
      draft,
    ),
  ).toBe(50);
  expect(rfStudyRadius(DEFAULT_RF_INPUTS, { ...draft, propagation: 'hf-groundwave' })).toBe(200);
  expect(() => rfStudyRadius(DEFAULT_RF_INPUTS, { ...draft, radiusMode: 'manual' })).toThrow(
    /Area to analyse/,
  );
});

it('keeps manual radius precise, bounded and distinct from automatic area selection', () => {
  const draft = { ...createRfDraft(), radiusMode: 'manual' as const };
  for (const radiusKm of ['0', '51', 'NaN', 'Infinity', ' '])
    expect(() =>
      rfStudyRadius(DEFAULT_RF_INPUTS, {
        ...draft,
        environment: { ...draft.environment!, radiusKm },
      }),
    ).toThrow();
  expect(
    rfStudyRadius(DEFAULT_RF_INPUTS, {
      ...draft,
      environment: { ...draft.environment!, radiusKm: '7.5' },
    }),
  ).toBe(7.5);
  expect(() => rfStudyRadius(DEFAULT_RF_INPUTS, { ...draft, propagation: 'hf-skywave' })).toThrow(
    /does not use/,
  );
});

it('suggests a single broader or closer pass based on sampled evidence', () => {
  const plan = createRfTerrainRadials([0, 0], 25);
  const strong = {
    ...DEFAULT_RF_INPUTS,
    transmitHeightM: 100,
    receiveHeightM: 100,
    transmitDbm: 50,
  };
  const passing = analyseRfTerrain(
    strong,
    plan,
    plan.positions.map(() => 0),
  );
  expect(rfRefinementRadius(passing)).toBe(50);
  const blocked = analyseRfTerrain(
    { ...strong, transmitHeightM: 0, receiveHeightM: 0 },
    plan,
    plan.positions.map(() => 0),
  );
  expect(rfRefinementRadius(blocked)).toBe(1);
  expect(
    rfRefinementRadius({
      ...passing,
      maxDistanceKm: 50,
      radials: passing.radials.map((radial) => ({ ...radial, clearDistanceKm: 50 })),
    }),
  ).toBeNull();
  expect(
    rfRefinementRadius({
      ...passing,
      radials: passing.radials.map((radial) => ({ ...radial, clearDistanceKm: 10 })),
    }),
  ).toBeNull();
});

it('never expands from missing terrain, bathymetry, a path study or an empty result', () => {
  const plan = createRfTerrainRadials([0, 0], 25);
  const result = analyseRfTerrain(
    DEFAULT_RF_INPUTS,
    plan,
    plan.positions.map(() => 0),
  );
  expect(rfRefinementRadius({ ...result, missingSamples: 1 })).toBeNull();
  expect(rfRefinementRadius({ ...result, belowSeaLevelSamples: 1 })).toBeNull();
  expect(rfRefinementRadius({ ...result, kind: 'path' })).toBeNull();
  expect(rfRefinementRadius({ ...result, radials: [] })).toBeNull();
  expect(rfRefinementRadius({ ...result, maxDistanceKm: NaN })).toBeNull();
  expect(
    rfRefinementRadius({
      ...result,
      radials: result.radials.map((radial) => ({ ...radial, status: 'unknown' })),
    }),
  ).toBeNull();
});

it('fits automatic polar studies to the existing provider budget and rejects unsupported positions', () => {
  expect(createAutomaticTerrainPlan([0, 51], 25).maxDistanceKm).toBe(25);
  const polar = createAutomaticTerrainPlan([0, 84], 50);
  expect(polar.maxDistanceKm).toBeLessThan(50);
  expect(polar.positions).toHaveLength(409);
  expect(() => createAutomaticTerrainPlan([0, 86], 25)).toThrow(/latitude/);
  expect(() => createAutomaticTerrainPlan([0, 85.051128], 25)).toThrow(/latitude/);
  expect(() => createAutomaticTerrainPlan([NaN, 0], 25)).toThrow();
  for (const radius of [0, 51, NaN, Infinity])
    expect(() => createAutomaticTerrainPlan([0, 0], radius)).toThrow(/radius/);
});
