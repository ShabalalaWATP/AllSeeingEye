import { describe, expect, it } from 'vitest';

import { DEPTH_TOKENS, HOSTING_SIZES, PRICE_PRESETS, USD_TO_GBP, pick } from './costModel';
import { estimate, formatMoney, formatRange, type EstimateInput } from './costing';

const base: EstimateInput = {
  analysts: 10,
  runsPerAnalystPerDay: 2,
  depth: {
    id: 'basic',
    label: 'Basic',
    inputLow: 100,
    inputHigh: 200,
    outputLow: 10,
    outputHigh: 20,
  },
  inputPrice: 2,
  outputPrice: 10,
  upliftPercent: 0,
  hosting: { id: 'h', label: 'H', spec: '', analysts: '', low: 20, high: 40 },
  currency: 'USD',
};

describe('cost estimate', () => {
  it('multiplies analysts, runs, working days and per-run token cost', () => {
    const result = estimate(base);
    // 10 analysts x 2 runs x 21 days = 420 runs.
    expect(result.runsPerMonth).toBe(420);
    // Low: 100k in x $2 + 10k out x $10 = $0.30 a run; high: $0.60 a run.
    expect(result.ai).toEqual({ low: 12600, high: 25200 });
  });

  it('adds the uplift for assistant, briefings and subscriptions', () => {
    expect(estimate({ ...base, upliftPercent: 50 }).ai).toEqual({ low: 18900, high: 37800 });
  });

  it('converts US dollar model costs and sterling hosting into the chosen currency', () => {
    const usd = estimate(base);
    const gbp = estimate({ ...base, currency: 'GBP' });
    expect(gbp.ai.low).toBe(Math.round(usd.ai.low * USD_TO_GBP));
    expect(gbp.hosting).toEqual({ low: 2000, high: 4000 });
    expect(usd.hosting.low).toBe(Math.round((20 / USD_TO_GBP) * 100));
    expect(gbp.total).toEqual({ low: gbp.ai.low + 2000, high: gbp.ai.high + 4000 });
  });

  it('clamps out-of-range and non-numeric inputs instead of producing nonsense', () => {
    const result = estimate({
      ...base,
      analysts: 100_000,
      runsPerAnalystPerDay: -3,
      inputPrice: Number.NaN,
      outputPrice: Number.POSITIVE_INFINITY,
    });
    expect(result.runsPerMonth).toBe(0);
    expect(result.ai).toEqual({ low: 0, high: 0 });
    expect(estimate({ ...base, analysts: 0.2 }).runsPerMonth).toBe(42);
  });

  it('formats money and ranges in British English', () => {
    expect(formatMoney(12345, 'GBP')).toBe('£123');
    expect(formatMoney(4550, 'USD')).toBe('US$45.50');
    expect(formatRange({ low: 1000, high: 1000 }, 'GBP')).toBe('£10.00');
    expect(formatRange({ low: 1000, high: 250000 }, 'GBP')).toBe('£10.00 to £2,500');
  });

  it('picks an option by id and falls back to the middle entry', () => {
    expect(pick(DEPTH_TOKENS, 'advanced').label).toBe('Advanced');
    expect(pick(HOSTING_SIZES, 'unknown')).toBe(HOSTING_SIZES[1]);
    expect(pick(PRICE_PRESETS, 'economy').input).toBeLessThan(
      pick(PRICE_PRESETS, 'frontier').input,
    );
  });
});
