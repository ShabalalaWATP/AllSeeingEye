import { expect, it } from 'vitest';
import { snapshotRfStudy, parseRfStudy } from './rfStudy';
import { createRfDraft } from './rfDraft';
import type { RfAnalysis } from './rfAnalysis';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { calculateHfSkywave } from './hfSkywave';
import { RF_ANTENNA_DEFAULTS } from './rfAntenna';
import { createRfTerrainRadials } from './rfTerrainSampling';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { measure } from './measurements';
const names = { origin: 'TX', receiver: 'RX' };
function groundwave(
  receiver: [number, number] | null,
): Extract<RfAnalysis, { kind: 'hf-groundwave' }> {
  return {
    kind: 'hf-groundwave',
    origin: [0, 0],
    receiver,
    input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 10 },
    result: {
      model: 'NTIA LFMF 1.1 (P.368-10)',
      status: 'calculated',
      source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
      limitations: 'Test scenario.',
      samples: [1, 20].map((distance, index) => ({
        distance_km: distance,
        basic_transmission_loss_db: 100 + index * 30,
        native_reference_field_dbuv_m: 40 - index * 20,
        received_power_dbm: -70 - index * 30,
        method: 'flat_earth',
      })),
    },
  };
}
it('archives area groundwave domain without inventing a receiver margin', () => {
  const analysis = groundwave(null);
  const saved = snapshotRfStudy(
    createRfDraft(analysis.input),
    analysis.origin,
    null,
    names,
    analysis,
  );
  expect(saved.result).toMatchObject({
    kind: 'hf-groundwave',
    status: 'calculated groundwave curve',
    distanceKm: 20,
    receivedDbm: null,
    marginDb: null,
    sampleCount: 2,
  });
  expect(saved.provenance.model).toContain('LFMF');
  expect(saved.provenance.limitations).toContain('Test scenario');
});
it.each([false, true])(
  'archives sampled and interpolated groundwave links (interpolated=%s)',
  (interpolated) => {
    const analysis = groundwave([0.1, 0]);
    if (!interpolated)
      analysis.result.samples[1]!.distance_km =
        measure([analysis.origin, analysis.receiver!], 'distance').metres / 1000;
    if (interpolated)
      analysis.engineering = { reserveDb: 10, obstacleHeightM: 0, earthFactor: 4 / 3 };
    const saved = snapshotRfStudy(
      createRfDraft(analysis.input),
      analysis.origin,
      analysis.receiver,
      names,
      analysis,
    );
    expect(saved.result?.status).toBe(
      `${interpolated ? 'interpolated' : 'sampled'} groundwave receiver`,
    );
    expect(saved.result?.receivedDbm).toBeTypeOf('number');
    expect(saved.result?.marginDb).toBeCloseTo(
      saved.result!.receivedDbm! - analysis.input.sensitivityDbm - (interpolated ? 10 : 0),
    );
  },
);
it('keeps a receiver outside the model interval unassessed', () => {
  const analysis = groundwave([1, 0]);
  const saved = snapshotRfStudy(
    createRfDraft(analysis.input),
    analysis.origin,
    analysis.receiver,
    names,
    analysis,
  );
  expect(saved.result?.receivedDbm).toBeNull();
  expect(saved.result?.distanceKm).toBe(20);
});
it.each([5, 30])(
  'archives HF geometry at %i MHz without a received-power claim',
  (frequencyMHz) => {
    const scenario = calculateHfSkywave({
      frequencyMHz,
      criticalFrequencyMHz: 5,
      virtualHeightKm: 300,
      minElevationDeg: 10,
      maxElevationDeg: 80,
    });
    const draft = {
      ...createRfDraft({ ...DEFAULT_RF_INPUTS, frequencyMHz }),
      propagation: 'hf-skywave' as const,
    };
    const saved = snapshotRfStudy(draft, [0, 0], null, names, {
      kind: 'hf-skywave',
      estimate: { origin: [0, 0], frequencyMHz, scenario },
    });
    expect(saved.result?.status).toBe(
      scenario.compatible ? 'compatible geometry' : 'no compatible hop',
    );
    expect(saved.result?.receivedDbm).toBeNull();
    expect(saved.provenance.limitations).toContain('Single hop');
  },
);
it('saves sampled terrain sectors separately from link margins and retains missing elevations as null', () => {
  const plan = createRfTerrainRadials([0, 0], 2);
  const elevations = plan.positions.map(() => 0);
  const terrain = analyseRfTerrain(DEFAULT_RF_INPUTS, plan, elevations);
  const saved = snapshotRfStudy(createRfDraft(), [0, 0], null, names, {
    kind: 'terrain',
    terrain,
    plan,
    input: DEFAULT_RF_INPUTS,
    elevations: {
      zoom: 10,
      resolution_m: 150,
      provider: 'Mapzen Terrain Tiles',
      elevations_m: elevations.slice(0, -1),
      attribution: 'DEM fixture',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Approximate.',
    },
  });
  expect(saved.result).toMatchObject({
    status: 'sampled sectors',
    receivedDbm: null,
    marginDb: null,
  });
  expect(saved.terrainEvidence?.samples.at(-1)?.[2]).toBeNull();
});
it('records valid directional free-space assumptions and refuses unsupported directional area modes', () => {
  const draft = {
    ...createRfDraft(),
    propagation: 'free-space' as const,
    study: 'link' as const,
    antenna: { ...RF_ANTENNA_DEFAULTS, enabled: true },
  };
  const saved = snapshotRfStudy(draft, [0, 0], [0.1, 0], names, null);
  expect(saved.provenance.limitations).toContain('idealised horizontal parabolic');
  expect(() => snapshotRfStudy({ ...draft, study: 'area' }, [0, 0], [0.1, 0], names, null)).toThrow(
    /receiver link/,
  );
  expect(() =>
    snapshotRfStudy({ ...draft, propagation: 'hf-groundwave' }, [0, 0], [0.1, 0], names, null),
  ).toThrow(/receiver link/);
  const area = snapshotRfStudy(
    { ...draft, study: 'area', antenna: { ...draft.antenna, enabled: false } },
    null,
    null,
    names,
    null,
  );
  expect(area.result?.distanceKm).toBe(10);
});
it.each(['blank', 'below', 'above', 'overlong'])(
  'rejects %s numeric fields before loading imported state',
  (condition) => {
    const saved = snapshotRfStudy(createRfDraft(), null, null, names, null);
    saved.draft.values.frequencyMHz = {
      blank: '',
      below: '0',
      above: '100001',
      overlong: '1'.repeat(41),
    }[condition]!;
    expect(() => parseRfStudy(saved)).toThrow();
  },
);
it('rejects oversized imported objects, malformed terrain lengths and non-increasing distances', () => {
  const saved = snapshotRfStudy(createRfDraft(), null, null, names, null);
  expect(() => parseRfStudy({ ...saved, padding: 'x'.repeat(128 * 1024) })).toThrow(/128 KiB/);
  const evidence = {
    zoom: 10,
    resolutionM: 150,
    samples: [
      [0, 0, 0],
      [0.1, 0, 0],
      [0.2, 0, 0],
    ],
    profiles: [{ bearingDegrees: 90, indices: [0, 1, 2], distancesM: [0, 1000, 2000] }],
  };
  for (const distancesM of [
    [0, 1000, 1000],
    [1, 1000, 2000],
    [0, 1000, 2000, 3000],
  ])
    expect(() =>
      parseRfStudy({
        ...saved,
        terrainEvidence: { ...evidence, profiles: [{ ...evidence.profiles[0], distancesM }] },
      }),
    ).toThrow();
});
