import { describe, expect, it } from 'vitest';

import {
  CURRENCIES,
  DEFAULT_UPLIFT,
  DEPTH_TOKENS,
  EXCHANGE_RATES,
  HOSTING_SIZES,
  PRICE_PRESETS,
  WORKING_DAYS,
  pick,
  type DepthTokens,
} from './costModel';
import {
  COST_MODEL,
  describeSample,
  estimate,
  formatCheckedOn,
  formatMoney,
  formatRange,
  fromGbpPounds,
  fromUsdCents,
  isStale,
  listAssumptions,
  staleAssumptions,
  summariseEstimate,
  SUMMARY_LIMIT,
  validateFigure,
  wholeUnits,
  type EstimateInput,
} from './costing';

const depth: DepthTokens = {
  id: 'basic',
  label: 'Basic',
  inputLow: 100,
  inputHigh: 200,
  outputLow: 10,
  outputHigh: 20,
  source: 'Test',
  checkedOn: '2026-10-07',
  sampleSize: null,
  sampledOn: null,
};

const base: EstimateInput = {
  analysts: 10,
  runsPerAnalystPerDay: 2,
  depth,
  inputPrice: 2,
  outputPrice: 10,
  upliftPercent: 0,
  hosting: {
    id: 'h',
    label: 'H',
    spec: '2 vCPU',
    analysts: '',
    low: 20,
    high: 40,
    source: 'Test',
    checkedOn: '2026-10-07',
  },
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

  it('converts US dollar model costs and sterling hosting into each currency', () => {
    const usd = estimate(base);
    const gbp = estimate({ ...base, currency: 'GBP' });
    const eur = estimate({ ...base, currency: 'EUR' });
    expect(gbp.ai.low).toBe(Math.round(usd.ai.low * EXCHANGE_RATES.USD.value));
    expect(gbp.hosting).toEqual({ low: 2000, high: 4000 });
    expect(usd.hosting.low).toBe(Math.round((20 / EXCHANGE_RATES.USD.value) * 100));
    expect(gbp.total).toEqual({ low: gbp.ai.low + 2000, high: gbp.ai.high + 4000 });
    // $126 is £94.50, which is €111.18 at £0.85 to the euro; £20 is €23.53.
    expect(eur.ai.low).toBe(11118);
    expect(eur.hosting.low).toBe(2353);
    expect(eur.total.low).toBe(eur.ai.low + eur.hosting.low);
  });

  it('rounds conversions once, to whole minor units', () => {
    expect(fromUsdCents(1, 'USD')).toBe(1);
    expect(fromUsdCents(3, 'GBP')).toBe(2);
    expect(fromUsdCents(100, 'EUR')).toBe(88);
    expect(fromGbpPounds(1, 'GBP')).toBe(100);
    expect(fromGbpPounds(1, 'USD')).toBe(133);
    expect(fromGbpPounds(1, 'EUR')).toBe(118);
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
    expect(estimate({ ...base, analysts: 500, runsPerAnalystPerDay: 40 }).runsPerMonth).toBe(
      420_000,
    );
  });

  it('formats money in whole units and collapses equal ranges', () => {
    expect(wholeUnits(12_350)).toBe(124);
    expect(formatMoney(12_345, 'GBP')).toBe('£123');
    expect(formatMoney(4550, 'USD')).toBe('US$46');
    expect(formatMoney(250_000_00, 'EUR')).toBe('€250,000');
    expect(formatRange({ low: 1000, high: 1040 }, 'GBP')).toBe('£10');
    expect(formatRange({ low: 1000, high: 250_000 }, 'GBP')).toBe('£10 to £2,500');
  });

  it('picks an option by id and falls back to the middle entry', () => {
    expect(pick(DEPTH_TOKENS, 'advanced').label).toBe('Advanced');
    expect(pick(HOSTING_SIZES, 'unknown')).toBe(HOSTING_SIZES[1]);
    expect(pick(PRICE_PRESETS, 'economy').input).toBeLessThan(
      pick(PRICE_PRESETS, 'frontier').input,
    );
    expect(CURRENCIES).toEqual(['GBP', 'USD', 'EUR']);
  });
});

describe('typed figures', () => {
  const analysts = { min: 1, max: 500, noun: 'Analysts', integer: true };

  it('accepts figures within range, including both limits', () => {
    expect(validateFigure('1', analysts)).toEqual({ ok: true, value: 1 });
    expect(validateFigure(' 500 ', analysts)).toEqual({ ok: true, value: 500 });
    expect(validateFigure('0.5', { min: 0, max: 40, noun: 'Runs' })).toEqual({
      ok: true,
      value: 0.5,
    });
  });

  it('explains blank, unreadable, fractional and out-of-range figures', () => {
    expect(validateFigure('', analysts)).toEqual({
      ok: false,
      message: 'Analysts is required: enter a whole number from 1 to 500.',
    });
    const outside = { ok: false, message: 'Analysts must be a whole number from 1 to 500.' };
    for (const text of ['0', '501', '2.5', 'ten', 'Infinity']) {
      expect(validateFigure(text, analysts)).toEqual(outside);
    }
    expect(validateFigure('1001', { min: 0, max: 1000, noun: 'Input price' })).toEqual({
      ok: false,
      message: 'Input price must be a number from 0 to 1,000.',
    });
  });

  it('uses the fallback for an optional blank figure but still checks typed ones', () => {
    const uplift = { min: 0, max: 200, noun: 'The extra', fallback: 25 };
    expect(validateFigure('  ', uplift)).toEqual({ ok: true, value: 25 });
    expect(validateFigure('201', uplift).ok).toBe(false);
  });
});

describe('figure review dates', () => {
  it('treats exactly 90 days as current and 91 days as stale', () => {
    expect(isStale('2026-10-07', new Date(2027, 0, 5))).toBe(false);
    expect(isStale('2026-10-07', new Date(2027, 0, 6))).toBe(true);
    expect(isStale('2026-10-07', new Date(2026, 9, 7, 23, 59))).toBe(false);
    expect(isStale('2026-10-07', new Date(2026, 9, 9), 1)).toBe(true);
    expect(isStale('2027-01-01', new Date(2026, 9, 9))).toBe(false);
  });

  it('formats checked dates in British English', () => {
    expect(formatCheckedOn('2026-10-07')).toBe('7 October 2026');
    expect(formatCheckedOn('soon')).toBe('soon');
  });

  it('counts unreadable dates as stale so they are never hidden', () => {
    expect(isStale('07/10/2026', new Date(2026, 9, 9))).toBe(true);
    expect(isStale('2026-13-40', new Date(2026, 9, 9))).toBe(true);
  });

  it('lists the figures that need review', () => {
    expect(staleAssumptions(new Date(2026, 9, 18))).toEqual([]);
    const stale = staleAssumptions(new Date(2027, 0, 6));
    // Everything except the euro rate, added on 18 October 2026.
    expect(stale.map((entry) => entry.id)).not.toContain('rate-EUR');
    expect(stale).toHaveLength(listAssumptions().length - 1);
  });
});

describe('assumptions disclosure', () => {
  it('lists every constant with its source and checked date', () => {
    const entries = listAssumptions();
    expect(entries).toHaveLength(3 + 3 + 3 + 1 + 1 + 2);
    for (const entry of entries) {
      expect(entry.source.length).toBeGreaterThan(10);
      expect(entry.checkedOn).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
    const byId = new Map(entries.map((entry) => [entry.id, entry]));
    expect(byId.get('hosting-small')?.value).toBe('£15 to £35 a month');
    expect(byId.get('tokens-deep')?.value).toBe(
      '300k to 650k input and 40k to 90k output tokens; sample: not yet measured',
    );
    expect(byId.get('tokens-deep')?.source).toMatch(/^Draft placeholder/);
    expect(byId.get('price-economy')?.value).toBe(
      'US$0.40 input and US$1.60 output per million tokens',
    );
    expect(byId.get('working-days')?.value).toBe(`${WORKING_DAYS.value}`);
    expect(byId.get('uplift')?.value).toBe(`${DEFAULT_UPLIFT.value} percent`);
    expect(byId.get('rate-EUR')?.value).toBe('£0.85');
  });

  it('describes a measured sample once one is recorded', () => {
    expect(describeSample(depth)).toBe('not yet measured');
    expect(describeSample({ ...depth, sampleSize: 1200, sampledOn: null })).toBe(
      'not yet measured',
    );
    const measured = { ...depth, sampleSize: 1200, sampledOn: '2026-11-01' };
    expect(describeSample(measured)).toBe('1,200 runs, exported 2026-11-01');
    const model = { ...COST_MODEL, depths: [measured] };
    expect(listAssumptions(model).find((entry) => entry.id === 'tokens-basic')?.value).toMatch(
      /sample: 1,200 runs/,
    );
    expect(staleAssumptions(new Date(2026, 9, 18), model)).toEqual([]);
  });
});

describe('enquiry summary', () => {
  it('summarises the inputs and ranges as plain text that says it is an estimate', () => {
    const text = summariseEstimate({ ...base, currency: 'GBP', upliftPercent: 25 }, 'Custom');
    expect(text).toMatch(/^Self-hosting running-cost estimate/);
    expect(text).toContain('This is an estimate, not a quote.');
    expect(text).toContain('The figures are drafts');
    expect(text).toContain('Analysts: 10');
    expect(text).toContain('Model prices: Custom, US$2.00 input and US$10.00 output');
    expect(text).toContain('Extra for the assistant, briefings and subscriptions: 25 percent');
    expect(text).toContain('Server size: H (2 vCPU)');
    expect(text).toContain('AI usage (420 runs a month): £118 to £236');
    expect(text).toContain('Server: £20 to £40');
    expect(text).toContain('Licence and support: quoted on enquiry');
    expect(text).not.toMatch(/[<>]/);
    expect(text.length).toBeLessThanOrEqual(SUMMARY_LIMIT);
  });

  it('drops the draft line once approved, uses the clamped figures and stays bounded', () => {
    const text = summariseEstimate({ ...base, analysts: 9000 }, 'Standard model', 'approved');
    expect(text).not.toContain('drafts');
    expect(text).toContain('Analysts: 500');
    const long = summariseEstimate(
      { ...base, hosting: { ...base.hosting, spec: 'x'.repeat(5000) } },
      'Custom',
    );
    expect(long).toHaveLength(SUMMARY_LIMIT);
  });
});
