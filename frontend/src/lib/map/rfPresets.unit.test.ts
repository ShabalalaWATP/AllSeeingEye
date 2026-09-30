import { expect, it } from 'vitest';
import { RF_PRESETS } from './rfPresets';
import { calculateRf } from './rfPlanning';

const byId = (id: string) => RF_PRESETS.find((preset) => preset.id === id)!;
const watts = (id: string) => 10 ** ((byId(id).values.transmitDbm - 30) / 10);

it('keeps unique stable IDs and every preset within calculator and propagation bounds', () => {
  expect(new Set(RF_PRESETS.map((preset) => preset.id)).size).toBe(RF_PRESETS.length);
  expect(byId('bowman-vhf-band').values.frequencyMHz).toBe(60);
  expect(byId('falcon-ii-hf')).toBeDefined();
  for (const preset of RF_PRESETS) {
    expect(() => calculateRf(preset.values)).not.toThrow();
    if (preset.propagation?.startsWith('hf-')) {
      expect(preset.values.frequencyMHz).toBeGreaterThanOrEqual(1.6);
      expect(preset.values.frequencyMHz).toBeLessThanOrEqual(30);
      expect(preset.values.transmitHeightM).toBeLessThanOrEqual(50);
    } else if (preset.propagation === 'terrain') {
      expect(preset.values.frequencyMHz).toBeGreaterThanOrEqual(30);
    }
    if (preset.group) {
      expect(new URL(preset.referenceUrl!).protocol).toBe('https:');
      expect(preset.referenceLabel).toBeTruthy();
    }
  }
});

it('labels Bowman settings as scenarios and provides HF groundwave, NVIS and VHF roles', () => {
  const bowman = RF_PRESETS.filter((preset) => preset.group === 'bowman');
  expect(bowman).toHaveLength(4);
  expect(bowman.every((preset) => preset.basis === 'illustrative')).toBe(true);
  expect(bowman.every((preset) => preset.specification === undefined)).toBe(true);
  expect(new Set(bowman.map((preset) => preset.propagation))).toEqual(
    new Set(['terrain', 'hf-groundwave', 'hf-skywave']),
  );
  expect(byId('bowman-prc325-nvis').environment).toEqual({
    minElevationDeg: '60',
    maxElevationDeg: '90',
  });
});

it('uses mode-specific product powers rather than burst or peak ratings for terrestrial FM', () => {
  expect(watts('prc150-hf')).toBeCloseTo(20);
  expect(watts('prc150-vhf')).toBeCloseTo(10);
  expect(watts('prc152a-vhf')).toBeCloseTo(5);
  expect(watts('prc152a-uhf')).toBeCloseTo(5);
  expect(watts('prc117g-narrowband')).toBeCloseTo(10);
  expect(watts('prc148-mbitr')).toBeCloseTo(5);
  expect(watts('sincgars-rt1702')).toBeCloseTo(5);
  expect(watts('sincgars-rt1702-rfpa')).toBeCloseTo(50);
  expect(byId('prc150-vhf').values.frequencyMHz).toBeLessThan(60);
  expect(byId('prc117g-narrowband').values.frequencyMHz).toBeLessThanOrEqual(512);
  expect(byId('sincgars-rt1702-rfpa').note).toMatch(/Requires the external RF power amplifier/);
});
