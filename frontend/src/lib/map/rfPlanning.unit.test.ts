import { expect, it } from 'vitest';
import { calculateRf, DEFAULT_RF_INPUTS } from './rfPlanning';

it('matches the free-space equation and preserves signed link margin', () => {
  const result = calculateRf({ ...DEFAULT_RF_INPUTS, frequencyMHz: 1000, distanceKm: 1 });
  expect(result.freeSpaceLossDb).toBeCloseTo(92.448, 2);
  expect(result.receivedDbm).toBeCloseTo(-60.448, 2);
  expect(result.marginDb).toBeCloseTo(39.552, 2);
  const weaker = calculateRf({ ...DEFAULT_RF_INPUTS, transmitDbm: -100 });
  expect(weaker.marginDb).toBeLessThan(0);
});

it('allows HF in the free-space baseline without adding a groundwave or skywave prediction', () => {
  const result = calculateRf({ ...DEFAULT_RF_INPUTS, frequencyMHz: 1.6 });
  expect(Number.isFinite(result.freeSpaceLossDb)).toBe(true);
  expect(() => calculateRf({ ...DEFAULT_RF_INPUTS, frequencyMHz: 1.59 })).toThrow(/Frequency/);
  expect(result.horizonKm).toBe(calculateRf(DEFAULT_RF_INPUTS).horizonKm);
});

it('increases path loss by6dB when distance doubles and flags beyond-horizon paths', () => {
  const a = calculateRf(DEFAULT_RF_INPUTS);
  const b = calculateRf({ ...DEFAULT_RF_INPUTS, distanceKm: 20 });
  expect(b.freeSpaceLossDb - a.freeSpaceLossDb).toBeCloseTo(6.0206, 3);
  expect(a.horizonKm).toBeCloseTo(18.86, 1);
  expect(b.beyondHorizon).toBe(true);
  expect(a.midpointFresnelM).toBeCloseTo(28.8575, 2);
});

it.each([0, NaN, Infinity, -1])('rejects invalid frequency %s', (frequencyMHz) => {
  expect(() => calculateRf({ ...DEFAULT_RF_INPUTS, frequencyMHz })).toThrow(/Frequency/);
});

it('inverts sensitivity into ideal distance and responds to power, loss and frequency', () => {
  const base = calculateRf(DEFAULT_RF_INPUTS);
  expect(base.sensitivityDistanceKm).toBeCloseTo(105.528, 2);
  expect(
    calculateRf({ ...DEFAULT_RF_INPUTS, distanceKm: base.sensitivityDistanceKm }).marginDb,
  ).toBeCloseTo(0, 8);
  const morePower = calculateRf({ ...DEFAULT_RF_INPUTS, transmitDbm: 50 });
  expect(morePower.sensitivityDistanceKm / base.sensitivityDistanceKm).toBeCloseTo(10, 8);
  const doubleFrequency = calculateRf({ ...DEFAULT_RF_INPUTS, frequencyMHz: 1800 });
  expect(doubleFrequency.sensitivityDistanceKm / base.sensitivityDistanceKm).toBeCloseTo(0.5, 8);
  const moreLoss = calculateRf({ ...DEFAULT_RF_INPUTS, lossesDb: 22 });
  expect(moreLoss.sensitivityDistanceKm / base.sensitivityDistanceKm).toBeCloseTo(0.1, 8);
});

it('keeps allowed extreme estimates finite and rejects nonfinite or out-of-range power', () => {
  const high = calculateRf({
    ...DEFAULT_RF_INPUTS,
    frequencyMHz: 30,
    transmitDbm: 100,
    transmitGainDbi: 80,
    receiveGainDbi: 80,
    lossesDb: 0,
    sensitivityDbm: -200,
  });
  expect(Number.isFinite(high.sensitivityDistanceKm)).toBe(true);
  expect(high.sensitivityDistanceKm).toBeGreaterThan(high.horizonKm);
  expect(() => calculateRf({ ...DEFAULT_RF_INPUTS, transmitDbm: Infinity })).toThrow(
    /Transmit power/,
  );
  expect(() => calculateRf({ ...DEFAULT_RF_INPUTS, transmitDbm: 1e308 })).toThrow(/Transmit power/);
});
