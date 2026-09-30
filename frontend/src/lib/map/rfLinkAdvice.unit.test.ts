import { expect, it } from 'vitest';
import type { RfAnalysis } from './rfAnalysis';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { createRfTerrainPath } from './rfTerrainSampling';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import { RF_PHYSICAL_REFERENCE } from './rfEngineering';
import { rfLinkAdvice } from './rfLinkAdvice';

function study(
  ground: (number | null)[],
  overrides = {},
): Extract<RfAnalysis, { kind: 'terrain' }> {
  const input = { ...DEFAULT_RF_INPUTS, transmitHeightM: 30, receiveHeightM: 30, ...overrides };
  const plan = createRfTerrainPath([0, 0], [0.02, 0], 5);
  const terrain = analyseRfTerrain(input, plan, ground, {
    ...RF_PHYSICAL_REFERENCE,
    reserveDb: 10,
  });
  return {
    kind: 'terrain',
    input,
    plan,
    terrain,
    elevations: {
      elevations_m: ground.map((value) => value ?? 0),
      zoom: 10,
      resolution_m: 150,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Fixture',
      attribution_url: 'https://example.com/',
      limitations: 'Fixture',
    },
  };
}

it('calculates a one-site height scenario that clears the same sampled obstruction without changing inputs', () => {
  const analysis = study([0, 0, 0, 150, 0]);
  const original = structuredClone(analysis);
  const advice = rfLinkAdvice(analysis);
  expect(advice?.kind).toBe('height');
  if (advice?.kind !== 'height') throw new Error('Expected a height scenario.');
  expect(advice.site).toBe('receiver');
  expect(advice.heightM).toBeGreaterThan(150);
  const profile = analysis.terrain.path!;
  const trial = evaluateRfTerrainProfile(
    { ...analysis.input, receiveHeightM: advice.heightM },
    profile.points.map((point) => point.position),
    profile.points.map((point) => point.distanceM),
    profile.points.map((point) => point.elevationM),
    analysis.terrain.engineering,
  );
  expect(trial.minimumFresnelClearanceM).toBeGreaterThan(0);
  expect(trial.status).toBe(advice.status);
  expect(trial.planningMarginDb).toBe(advice.planningMarginDb);
  expect(analysis).toEqual(original);
});

it('does not claim that mast height fixes a simultaneous power shortfall', () => {
  const advice = rfLinkAdvice(study([0, 0, 100, 0, 0], { transmitDbm: -100 }));
  expect(advice).toMatchObject({ kind: 'height', status: 'risk' });
  if (advice?.kind === 'height') expect(advice.planningMarginDb).toBeLessThan(0);
});

it('quantifies a clear-path reserve shortfall separately from geometry', () => {
  const analysis = study([0, 0, 0, 0, 0], { transmitDbm: -100 });
  const advice = rfLinkAdvice(analysis);
  expect(advice).toEqual({
    kind: 'budget',
    shortfallDb: -analysis.terrain.path!.planningMarginDb!,
  });
  expect(rfLinkAdvice(study([0, 0, 0, 0, 0]))).toBeNull();
});

it('withholds height advice for uncertain ground and unsupported heights', () => {
  expect(rfLinkAdvice(study([0, null, 100, 0, 0]))).toBeNull();
  expect(rfLinkAdvice(study([0, -10, 100, 0, 0]))).toBeNull();
  expect(rfLinkAdvice(study([0, 0, 10000, 0, 0]))).toBeNull();
  const area = study([0, 0, 0, 0, 0]);
  area.terrain.path = null;
  area.terrain.kind = 'radial';
  expect(rfLinkAdvice(area)).toBeNull();
});

it('limits proposed heights to feasible site ceilings without altering the current study', () => {
  const analysis = study([0, 0, 0, 150, 0]);
  expect(rfLinkAdvice(analysis, { transmitter: 30, receiver: 30 })).toBeNull();
  const unlimited = rfLinkAdvice(analysis);
  expect(unlimited?.kind).toBe('height');
  if (unlimited?.kind === 'height')
    expect(rfLinkAdvice(analysis, { [unlimited.site]: unlimited.heightM })).toEqual(unlimited);
});
