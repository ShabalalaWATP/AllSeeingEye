import { expect, it } from 'vitest';
import { antennaAttenuation, directionalRfInputs, RF_ANTENNA_DEFAULTS } from './rfAntenna';
import { calculateRf, DEFAULT_RF_INPUTS } from './rfPlanning';
import { rfPlannerInputs } from './rfPlannerInputs';
import { createRfDraft } from './rfDraft';
it('has zero boresight loss, -3 dB at half beamwidth and a bounded back lobe', () => {
  expect(antennaAttenuation(90, 90, 60, 20)).toBe(0);
  expect(antennaAttenuation(120, 90, 60, 20)).toBe(3);
  expect(antennaAttenuation(60, 90, 60, 20)).toBe(3);
  expect(antennaAttenuation(270, 90, 60, 20)).toBe(20);
  expect(antennaAttenuation(0, 360, 60, 20)).toBe(0);
  expect(() => antennaAttenuation(90, 0, 0, 20)).toThrow();
});
it('uses the receiver-to-transmitter bearing and never changes equipment gain', () => {
  const aligned = directionalRfInputs(DEFAULT_RF_INPUTS, [0, 0], [0.1, 0], {
    ...RF_ANTENNA_DEFAULTS,
    enabled: true,
    transmitterBearing: '90',
    receiverBearing: '270',
  });
  expect(aligned.lossesDb).toBeCloseTo(DEFAULT_RF_INPUTS.lossesDb);
  const misaligned = directionalRfInputs(DEFAULT_RF_INPUTS, [0, 0], [0.1, 0], {
    ...RF_ANTENNA_DEFAULTS,
    enabled: true,
    transmitterBearing: '270',
    receiverBearing: '90',
  });
  expect(misaligned.lossesDb).toBe(DEFAULT_RF_INPUTS.lossesDb);
  expect(misaligned.directionalLossDb).toBe(40);
  expect(calculateRf(misaligned).receivedDbm).toBeCloseTo(
    calculateRf(DEFAULT_RF_INPUTS).receivedDbm - 40,
  );
  expect(misaligned.transmitGainDbi).toBe(DEFAULT_RF_INPUTS.transmitGainDbi);
});
it('rejects directional area/HF studies without silently applying an omnidirectional model', () => {
  const draft = { ...createRfDraft(), antenna: { ...RF_ANTENNA_DEFAULTS, enabled: true } };
  expect(rfPlannerInputs(draft, [0, 0], null).error).toMatch(/receiver link/);
  expect(
    rfPlannerInputs({ ...draft, propagation: 'hf-groundwave' }, [0, 0], [0.1, 0]).error,
  ).toMatch(/receiver link/);
  expect(() => directionalRfInputs(DEFAULT_RF_INPUTS, [0, 0], [0, 0], draft.antenna)).toThrow(
    /Separate/,
  );
});

it('accepts the full bounded pattern attenuation separately from the cable loss field', () => {
  const input = directionalRfInputs(DEFAULT_RF_INPUTS, [0, 0], [0.1, 0], {
    ...RF_ANTENNA_DEFAULTS,
    enabled: true,
    transmitterBearing: '270',
    receiverBearing: '90',
    beamwidth: '1',
    maximumAttenuation: '60',
  });
  expect(input.directionalLossDb).toBe(120);
  expect(() => calculateRf(input)).not.toThrow();
});
