import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import type { GroundwaveResult } from '@/lib/api/groundwave';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { hfGroundwaveLayers, hfGroundwaveReceiver, hfGroundwaveSummary } from './hfGroundwaveMap';
import type { RfAnalysis } from './rfAnalysis';
import type { Position } from './geoJsonTypes';

function model(powers = [-80, -90, -110, -120]): GroundwaveResult {
  return {
    model: 'NTIA LFMF 1.1 (P.368-10)',
    status: 'calculated',
    source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
    limitations: 'Homogeneous ground only',
    samples: powers.map((received_power_dbm, index) => ({
      distance_km: [1, 10, 100, 200][index]!,
      basic_transmission_loss_db: 100,
      native_reference_field_dbuv_m: 30,
      received_power_dbm,
      method: 'flat_earth',
    })),
  };
}

it('uses the last passing sample before the first failure, not an interpolated or later island radius', () => {
  expect(hfGroundwaveSummary(model(), -100)).toEqual({
    radiusKm: 10,
    firstFailureKm: 100,
    checkedFromKm: 1,
    checkedToKm: 200,
    passingSamples: 2,
    atLimit: false,
    noPassing: false,
  });
  expect(hfGroundwaveSummary(model([-80, -110, -80, -80]), -100).radiusKm).toBe(1);
});

it('distinguishes no passing samples from all samples passing at the search limit', () => {
  expect(hfGroundwaveSummary(model([-110, -120, -130, -140]), -100)).toMatchObject({
    radiusKm: null,
    firstFailureKm: 1,
    noPassing: true,
    atLimit: false,
  });
  expect(hfGroundwaveSummary(model([-80, -90, -100, -100]), -100)).toMatchObject({
    radiusKm: 200,
    firstFailureKm: null,
    noPassing: false,
    atLimit: true,
  });
});

it('interpolates model power on log distance and never extrapolates beyond the sample domain', () => {
  expect(hfGroundwaveReceiver(model(), Math.sqrt(10))).toMatchObject({
    receivedDbm: -85,
    modelOnly: true,
    interpolated: true,
  });
  expect(hfGroundwaveReceiver(model(), 10)).toMatchObject({
    receivedDbm: -90,
    interpolated: false,
  });
  expect(hfGroundwaveReceiver(model(), 1)?.receivedDbm).toBe(-80);
  expect(hfGroundwaveReceiver(model(), 200)?.receivedDbm).toBe(-120);
  for (const distance of [0, 0.999, 201, NaN, Infinity])
    expect(hfGroundwaveReceiver(model(), distance)).toBeNull();
});

it('rejects unsorted, duplicate, nonfinite and unbounded model input', () => {
  expect(() => hfGroundwaveSummary(model(), NaN)).toThrow(/sensitivity/);
  expect(() => hfGroundwaveSummary({ ...model(), samples: [] }, -100)).toThrow(/samples/);
  for (const distance of [0.5, 10, 201, NaN]) {
    const value = model();
    value.samples[2]!.distance_km = distance;
    expect(() => hfGroundwaveSummary(value, -100)).toThrow(/increasing distances/);
  }
  expect(() => hfGroundwaveReceiver(model([-80, NaN, -100, -120]), 10)).toThrow(/finite power/);
});

function analysis(distanceKm: number): Extract<RfAnalysis, { kind: 'hf-groundwave' }> {
  const origin: Position = [179.99, 1];
  const end = Geodesic.WGS84.Direct(origin[1], origin[0], 90, distanceKm * 1000);
  return {
    kind: 'hf-groundwave',
    result: model(),
    origin,
    receiver: [end.lon2!, end.lat2!],
    input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 7 },
  };
}

it('renders bounded reference rings and a receiver path only inside the model domain', () => {
  const within = hfGroundwaveLayers(analysis(20), true);
  const paths = within[0]?.props.data as { path: Position[] }[];
  expect(paths).toHaveLength(4);
  expect(paths.slice(0, 3).every((item) => item.path.length === 73)).toBe(true);
  expect(paths[3]?.path).toHaveLength(65);
  expect(
    paths
      .flatMap((item) => item.path)
      .every(([lon, lat]) => Math.abs(lon) <= 180 && Math.abs(lat) <= 90),
  ).toBe(true);
  expect(within.every((layer) => layer.props.pickable === false)).toBe(true);
  expect(hfGroundwaveLayers(analysis(0.5), true)[0]?.props.data).toHaveLength(3);
  expect(hfGroundwaveLayers(analysis(201), true)[0]?.props.data).toHaveLength(3);
  expect(hfGroundwaveLayers({ ...analysis(20), receiver: null }, true)[1]?.props.data).toHaveLength(
    1,
  );
  expect(hfGroundwaveLayers(null, false)).toEqual([]);
});

it('avoids claiming a zero range when the first sample fails and handles polar sites', () => {
  const failed = { ...analysis(20), result: model([-120, -130, -140, -150]), receiver: null };
  expect(hfGroundwaveLayers(failed, false)[0]?.props.data).toHaveLength(1);
  const polar = hfGroundwaveLayers({ ...failed, origin: [0, 90] }, true);
  expect(polar[1]?.props.data).toEqual([]);
  expect(polar[2]?.props.data).toEqual([]);
});
