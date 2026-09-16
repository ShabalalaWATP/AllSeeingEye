import { describe, expect, it } from 'vitest';

import { aiPrices, aiTotals } from '@/test/fixtures.aiUsage';

import { SPEND_CAVEAT, formatSpend, spendOf } from './spend';

describe('estimated spend', () => {
  it('formats a normal amount at the configured currency', () => {
    expect(formatSpend('6.4321', aiPrices())).toBe('USD 6.43');
    expect(formatSpend('6.4321', aiPrices({ currency: 'GBP' }))).toBe('GBP 6.43');
  });

  it('keeps four places below a cent so a small call is not shown as nothing', () => {
    expect(formatSpend('0.0026', aiPrices())).toBe('USD 0.0026');
    expect(formatSpend('0.0000', aiPrices())).toBe('USD 0.00');
  });

  it('shows nothing when no price is configured', () => {
    const free = aiPrices({ input_per_million: 0, output_per_million: 0, configured: false });
    expect(formatSpend('1.0000', free)).toBeNull();
    expect(spendOf(aiTotals({ estimated_cost: null }), free)).toBeNull();
  });

  it('shows nothing when the server sent no estimate', () => {
    expect(spendOf(aiTotals({ estimated_cost: null }), aiPrices())).toBeNull();
  });

  it('ignores an unusable figure rather than rendering NaN', () => {
    expect(formatSpend('not a number', aiPrices())).toBeNull();
  });

  it('uses a custom price without recomputing the server estimate', () => {
    const custom = aiPrices({ input_per_million: 3, output_per_million: 15, currency: 'EUR' });
    expect(spendOf(aiTotals({ estimated_cost: '33.0000' }), custom)).toBe('EUR 33.00');
  });

  it('never calls the figure a bill', () => {
    expect(SPEND_CAVEAT).toContain('not a bill');
  });
});
