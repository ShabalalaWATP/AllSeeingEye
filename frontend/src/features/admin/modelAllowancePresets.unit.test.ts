import { describe, expect, it } from 'vitest';

import { aiPolicy } from '@/test/fixtures.aiUsage';

import {
  ALLOWANCE_PRESETS,
  allowancePresetLimits,
  currentAllowancePreset,
  describeAllowanceLimits,
  describePreset,
} from './modelAllowancePresets';

describe('daily allowance presets', () => {
  it.each(ALLOWANCE_PRESETS)('recognises the exact $label daily policy', (preset) => {
    const limits = allowancePresetLimits(preset.value);
    expect(limits).toEqual({
      request_limit: preset.request_limit,
      token_limit: preset.token_limit,
    });
    expect(currentAllowancePreset([aiPolicy({ ...limits, period: 'day' })])).toBe(preset.value);
  });

  it('does not mistake a weekly, monthly or disabled policy for a daily preset', () => {
    const limits = allowancePresetLimits('standard');
    expect(
      currentAllowancePreset([
        aiPolicy({ ...limits, period: 'week' }),
        aiPolicy({ ...limits, period: 'month' }),
        aiPolicy({ ...limits, period: 'day', enabled: false }),
      ]),
    ).toBe('inherit');
  });

  it('preserves non-preset limits, including one-sided blocking, as custom', () => {
    expect(currentAllowancePreset([aiPolicy({ period: 'day' })])).toBe('custom');
    expect(currentAllowancePreset([aiPolicy({ period: 'day', request_limit: 0 })])).toBe('custom');
    expect(currentAllowancePreset([aiPolicy({ period: 'day', request_limit: null })])).toBe(
      'custom',
    );
    expect(currentAllowancePreset([aiPolicy({ period: 'day' }), aiPolicy({ period: 'day' })])).toBe(
      'custom',
    );
  });

  it('describes exact limits without suggesting inherited usage is unlimited', () => {
    expect(describePreset('standard', [])).toBe('250 requests · 500,000 tokens per day');
    expect(describePreset('inherit', [])).toBe('Other applicable limits still apply.');
    expect(describePreset('blocked', [])).toBe('Daily requests blocked.');
    expect(describePreset('custom', [aiPolicy({ period: 'day' })])).toBe(
      '10 requests · 1,000 tokens',
    );
    expect(describeAllowanceLimits({ request_limit: null, token_limit: null })).toBe(
      'no separate request cap · no separate token cap',
    );
  });
});
