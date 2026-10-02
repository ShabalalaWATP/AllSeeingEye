import { expect, it } from 'vitest';
import { analysisExplanation, freeSpaceExplanation } from './rfResultExplanation';
import { calculateRf, DEFAULT_RF_INPUTS } from './rfPlanning';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import type { RfAnalysis } from './rfAnalysis';
import type { RfTerrainRadial } from './rfTerrainTypes';
import { RF_PHYSICAL_REFERENCE } from './rfEngineering';

function terrain(
  ground: (number | null)[] = [0, 0, 0],
  overrides = {},
  reserve = 10,
): Extract<RfAnalysis, { kind: 'terrain' }> {
  const input = { ...DEFAULT_RF_INPUTS, transmitHeightM: 30, receiveHeightM: 30, ...overrides };
  const positions: [number, number][] = [
    [0, 0],
    [0.01, 0],
    [0.02, 0],
  ];
  const path = evaluateRfTerrainProfile(input, positions, [0, 1000, 2000], ground, {
    ...RF_PHYSICAL_REFERENCE,
    reserveDb: reserve,
  });
  return {
    kind: 'terrain',
    input,
    plan: {
      kind: 'path',
      origin: [0, 0],
      receiver: [0.02, 0],
      maxDistanceKm: 2,
      positions,
      profiles: [{ bearingDegrees: 90, indices: [0, 1, 2], distancesM: [0, 1000, 2000] }],
    },
    elevations: {
      elevations_m: ground.map((value) => value ?? 0),
      zoom: 10,
      resolution_m: 150,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Test fixture',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Test fixture',
    },
    terrain: {
      kind: 'path',
      origin: [0, 0],
      receiver: [0.02, 0],
      maxDistanceKm: 2,
      path,
      radials: [],
      warnings: [],
      sampleCount: 3,
      missingSamples: ground.filter((value) => value === null).length,
      belowSeaLevelSamples: ground.filter((value) => value !== null && value < 0).length,
    },
  };
}
function radial(status: RfTerrainRadial['status'], distance: number): RfTerrainRadial {
  return {
    bearingDegrees: 90,
    clearDistanceKm: distance,
    stopDistanceKm: status === 'clear' ? null : 2,
    status,
    samples: [],
  };
}
function area(radials: RfTerrainRadial[], missing = 0) {
  const value = terrain();
  value.terrain = {
    ...value.terrain,
    kind: 'radial',
    receiver: null,
    path: null,
    radials,
    missingSamples: missing,
  };
  return value;
}
it('qualifies a favourable free-space result as an unverified ideal-path calculation', () => {
  const result = calculateRf({ ...DEFAULT_RF_INPUTS, distanceKm: 1 });
  const copy = structuredClone(result);
  const text = freeSpaceExplanation(result);
  expect(text.tone).toBe('pass');
  expect(text.explanation).toContain('extra allowance you chose');
  expect(text.limitations).toMatch(/Terrain.*interference.*noise/);
  expect(result).toEqual(copy);
});
it.each([true, false])(
  'does not turn favourable power into a direct-link claim beyond the horizon (weak=%s)',
  (weak) => {
    const text = freeSpaceExplanation(
      calculateRf({ ...DEFAULT_RF_INPUTS, distanceKm: 1000, sensitivityDbm: weak ? -50 : -200 }),
    );
    expect(text.tone).toBe('caution');
    expect(text.headline).toContain('radio horizon');
    expect(text.explanation.includes('also below')).toBe(weak);
    expect(text.nextStep).toContain('terrain profile');
  },
);
it('distinguishes weak signal, missing reserve and exact threshold without changing zero into failure', () => {
  const input = { ...DEFAULT_RF_INPUTS, distanceKm: 1 };
  const received = calculateRf(input).receivedDbm;
  const weak = freeSpaceExplanation(
    calculateRf(
      { ...input, sensitivityDbm: received + 1 },
      { ...RF_PHYSICAL_REFERENCE, reserveDb: 10 },
    ),
  );
  expect(weak.headline).toContain('too weak for your receiver');
  const reserve = freeSpaceExplanation(
    calculateRf(
      { ...input, sensitivityDbm: received - 5 },
      { ...RF_PHYSICAL_REFERENCE, reserveDb: 10 },
    ),
  );
  expect(reserve.headline).toContain('meets the receiver setting');
  const exact = freeSpaceExplanation(
    calculateRf(
      { ...input, sensitivityDbm: received - 10 },
      { ...RF_PHYSICAL_REFERENCE, reserveDb: 10 },
    ),
  );
  expect(exact.tone).toBe('caution');
  expect(exact.headline).toContain('only just meets');
  expect(exact.explanation).toContain('meets');
  const zero = freeSpaceExplanation(calculateRf({ ...input, sensitivityDbm: received }));
  expect(zero.headline).toContain('only just meets');
  expect(zero.nextStep).toContain('Actual noise');
});
it('gives an obstruction priority over a favourable signal margin', () => {
  const analysis = terrain([0, 100, 0]);
  expect(analysis.terrain.path?.marginDb).toBeGreaterThan(0);
  const text = analysisExplanation(analysis);
  expect(text.tone).toBe('blocked');
  expect(text.explanation).toContain('does not remove that obstruction');
  expect(text.explanation).toContain('does not mean zero reception');
});
it('explains a Fresnel restriction around an otherwise clear direct line', () => {
  const analysis = terrain([0, 28, 0]);
  expect(analysis.terrain.path?.minimumLosClearanceM).toBeGreaterThan(0);
  expect(analysis.terrain.path?.minimumFresnelClearanceM).toBeLessThan(0);
  const text = analysisExplanation(analysis);
  expect(text.tone).toBe('caution');
  expect(text.explanation).toContain('space around the direct path');
  expect(text.headline).toContain('direct path is clear');
});
it('explains signal and reserve shortfalls separately and retains simultaneous clearance concerns', () => {
  const weak = analysisExplanation(terrain([0, 0, 0], { transmitDbm: -100 }));
  expect(weak.headline).toContain('too weak for your receiver');
  const reference = terrain([0, 0, 0]);
  const reserve = analysisExplanation(
    terrain([0, 0, 0], { sensitivityDbm: reference.terrain.path!.receivedDbm! - 5 }),
  );
  expect(reserve.headline).toContain('meets the receiver setting');
  const combined = analysisExplanation(terrain([0, 28, 0], { transmitDbm: -100 }));
  expect(combined.explanation).toContain(
    'clearance needed around the direct path is also restricted',
  );
  expect(combined.nextStep).toContain('Fixing signal margin alone');
});
it('qualifies a clear terrain path, preserves zero margin, and supports older profiles without reserve fields', () => {
  const value = terrain();
  const before = structuredClone(value);
  expect(analysisExplanation(value).tone).toBe('pass');
  expect(value).toEqual(before);
  const exact = terrain([0, 0, 0], { sensitivityDbm: value.terrain.path!.receivedDbm! - 10 });
  expect(analysisExplanation(exact).headline).toContain('only just meets');
  delete value.terrain.path!.planningMarginDb;
  delete value.terrain.path!.reserveDb;
  expect(analysisExplanation(value).tone).toBe('pass');
});
it.each([
  'missing-profile',
  'missing-ground',
  'missing-margin',
  'missing-planning-margin',
  'missing-line',
  'missing-space',
  'missing-count',
] as const)('keeps %s unknown rather than displaying a pass', (reason) => {
  const value = terrain();
  if (reason === 'missing-profile') value.terrain.path = null;
  if (reason === 'missing-ground') {
    const missing = terrain([0, null, 0]);
    expect(analysisExplanation(missing).tone).toBe('unknown');
    return;
  }
  if (reason === 'missing-margin') value.terrain.path!.marginDb = null;
  if (reason === 'missing-planning-margin') value.terrain.path!.planningMarginDb = null;
  if (reason === 'missing-line') value.terrain.path!.minimumLosClearanceM = null;
  if (reason === 'missing-space') value.terrain.path!.minimumFresnelClearanceM = null;
  if (reason === 'missing-count') value.terrain.missingSamples = 1;
  const text = analysisExplanation(value);
  expect(text.tone).toBe('unknown');
  expect(text.explanation).toContain('empty result does not mean');
});
it('keeps uncertain below-sea-level source heights prominent even when numerical checks pass', () => {
  const text = analysisExplanation(terrain([-10, -10, -10]));
  expect(text.tone).toBe('caution');
  expect(text.headline).toContain('ground and water');
  expect(text.limitations).toContain('seabed');
  expect(text.nextStep).toContain('land or water');
});
it('does not discard an explicit risk flag when available numeric checks look favourable', () => {
  const value = terrain();
  value.terrain.path!.status = 'risk';
  expect(analysisExplanation(value)).toMatchObject({
    tone: 'caution',
    headline: 'The checked path needs further review',
  });
});
it('explains mixed radial results without calling the whole area covered', () => {
  const text = analysisExplanation(area([radial('clear', 2), radial('risk', 1)]));
  expect(text.tone).toBe('caution');
  expect(text.headline).toContain('study has limits');
  expect(text.explanation).toContain('not a continuous coverage boundary');
  expect(text.limitations).toContain('Space between');
});
it('labels a fully passing radial screen as sampled to the limit, never a maximum range', () => {
  const text = analysisExplanation(area([radial('clear', 2), radial('clear', 2)]));
  expect(text.tone).toBe('caution');
  expect(text.headline).toContain('study limit');
  expect(text.explanation).toContain('not a maximum range');
  expect(text.nextStep).toContain('receiver');
});
it('distinguishes no passing paths from unassessed terrain in area studies', () => {
  const failed = analysisExplanation(area([radial('blocked', 0), radial('risk', 0)]));
  expect(failed.tone).toBe('caution');
  expect(failed.explanation).toContain('does not establish');
  const partial = analysisExplanation(area([radial('clear', 1), radial('unknown', 0)]));
  expect(partial.tone).toBe('unknown');
  expect(partial.explanation).toContain('Some sampled paths passed');
  const missing = analysisExplanation(area([radial('unknown', 0)], 1));
  expect(missing.tone).toBe('unknown');
  expect(missing.explanation).toContain('not evidence of no reception');
  expect(analysisExplanation(area([])).tone).toBe('unknown');
});

it('treats zero direct-path clearance as obstructed, matching the engine boundary', () => {
  const value = terrain();
  value.terrain.path!.minimumLosClearanceM = 0;
  value.terrain.path!.status = 'blocked';
  expect(analysisExplanation(value).tone).toBe('blocked');
});
