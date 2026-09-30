import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { analysisExplanation } from './rfResultExplanation';
import type { RfAnalysis } from './rfAnalysis';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { measure } from './measurements';
import { calculateHfSkywave } from './hfSkywave';

function groundwave(
  powers: number[],
  distanceKm: number | null = null,
): Extract<RfAnalysis, { kind: 'hf-groundwave' }> {
  const point = distanceKm === null ? null : Geodesic.WGS84.Direct(0, 0, 90, distanceKm * 1000);
  return {
    kind: 'hf-groundwave',
    origin: [0, 0],
    receiver: point ? [point.lon2!, point.lat2!] : null,
    input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 10 },
    engineering: { reserveDb: 10, obstacleHeightM: 0, earthFactor: 4 / 3 },
    result: {
      model: 'NTIA LFMF 1.1 (P.368-10)',
      status: 'calculated',
      source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
      limitations: 'Fixture',
      samples: powers.map((power, index) => ({
        distance_km: index + 1,
        received_power_dbm: power,
        basic_transmission_loss_db: 100,
        native_reference_field_dbuv_m: 10,
        method: 'flat_earth',
      })),
    },
  };
}
it('bases a receiver verdict on its own signal even when the first range sample fails', () => {
  const value = groundwave([-120, -80, -70], 2);
  const text = analysisExplanation(value);
  expect(text.tone).toBe('pass');
  expect(text.headline).toContain('meets your settings');
  expect(text.explanation).not.toContain('No passing range');
  expect(text.limitations).toContain('actual noise');
});
it('does not present the passing range near the transmitter as a pass at a failing receiver', () => {
  const text = analysisExplanation(groundwave([-70, -80, -120], 2.9));
  expect(text.tone).toBe('caution');
  expect(text.headline).toContain('too weak for your receiver');
  expect(text.explanation).toContain('neighbouring model samples');
});
it.each([0.5, 4])(
  'keeps a receiver at %s km outside the sampled interval unknown even when the whole curve passes',
  (distance) => {
    const text = analysisExplanation(groundwave([-80, -80, -80], distance));
    expect(text.tone).toBe('unknown');
    expect(text.explanation).toContain('1 to 3 km');
    expect(text.nextStep).toContain('Do not extend');
  },
);
it('distinguishes an exact receiver sample at the planning threshold from a failed link', () => {
  const value = groundwave([-80, -90, -95], 2);
  value.result.samples[1]!.distance_km =
    measure([value.origin, value.receiver!], 'distance').metres / 1000;
  const text = analysisExplanation(value);
  expect(text.tone).toBe('caution');
  expect(text.headline).toContain('only just meets');
  expect(text.explanation).toContain('matches a checked model distance');
});
it('explains a receiver which reaches sensitivity but misses the selected allowance', () => {
  const text = analysisExplanation(groundwave([-95, -95, -95], 1.5));
  expect(text.headline).toContain('meets the receiver setting');
  expect(text.nextStep).toContain('Do not remove');
});
it('supports legacy groundwave analyses with no reserve settings', () => {
  const value = groundwave([-95, -95, -95], 1.5);
  delete value.engineering;
  expect(analysisExplanation(value).tone).toBe('pass');
});
it('does not extend a range past first failure to later isolated passing samples', () => {
  const value = groundwave([-80, -100, -70]);
  const original = structuredClone(value);
  const text = analysisExplanation(value);
  expect(text.headline).toContain('between checked distances');
  expect(text.explanation).toContain('through 1 km');
  expect(text.explanation).toContain('2 km');
  expect(text.explanation).toContain('later isolated passing');
  expect(value).toEqual(original);
});
it('does not say no samples pass when only the first sample fails', () => {
  const text = analysisExplanation(groundwave([-110, -80, -70]));
  expect(text.headline).toContain('No passing range');
  expect(text.explanation).toContain('first checked distance');
  expect(text.explanation).toContain('Closer distances are unassessed');
});
it('labels a passing curve only through the search limit including exact-threshold samples', () => {
  const text = analysisExplanation(groundwave([-90, -90, -90]));
  expect(text.tone).toBe('caution');
  expect(text.explanation).toContain('Every checked distance meets');
  expect(text.explanation).toContain('search limit, not an established maximum range');
});
it.each([5, 30])('keeps %i MHz skywave results as geometry only', (frequencyMHz) => {
  const scenario = calculateHfSkywave({
    frequencyMHz,
    criticalFrequencyMHz: 5,
    virtualHeightKm: 300,
    minElevationDeg: 10,
    maxElevationDeg: 80,
  });
  const analysis: RfAnalysis = {
    kind: 'hf-skywave',
    estimate: { origin: [0, 0], frequencyMHz, scenario },
  };
  const text = analysisExplanation(analysis);
  expect(text.tone).toBe('scenario');
  expect(text.headline).toBe(
    scenario.compatible
      ? 'This shows travel distances only'
      : 'No travel distance fits these settings',
  );
  expect(text.limitations).toContain('No current atmospheric readings');
  expect(text.limitations).toContain('power and mast height do not determine');
  expect(text.nextStep).toContain('atmospheric conditions');
});
