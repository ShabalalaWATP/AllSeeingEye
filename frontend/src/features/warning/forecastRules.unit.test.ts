import { describe, expect, it } from 'vitest';

import {
  emptyRuleFields,
  ruleFieldsFromIndicator,
  ruleProblems,
  ruleRequest,
  ruleSummary,
} from '@/lib/alertRules';
import { indicator } from '@/test/fixtures.warning';

import { ruleUpdate } from './ruleUpdates';

const ratioRule = { ...indicator, baseline_ratio: 2.5, baseline_days: 14, window_minutes: 60 };
const scope = { teamId: '', bbox: undefined, geometry: undefined };
const context = { knownCountries: new Set(['UA']) };

describe('forecast ratio settings in the current alert rule editor', () => {
  it('preserves the ratio and selected cohort through a rename, pause and resume', () => {
    const fields = ruleFieldsFromIndicator(ratioRule);
    const edited = ruleRequest({ ...fields, name: 'Renamed' }, scope);
    expect(edited).toMatchObject({ baseline_ratio: 2.5, baseline_days: 14, window_minutes: 60 });
    expect(ruleUpdate(ratioRule, edited, false)).toMatchObject({
      name: 'Renamed',
      expected_updated_at: ratioRule.updated_at,
      baseline_ratio: 2.5,
    });
    const paused = ruleUpdate(ratioRule, null, false);
    expect(paused).toMatchObject({ enabled: false, baseline_ratio: 2.5, baseline_days: 14 });
    expect(ruleUpdate({ ...ratioRule, enabled: false }, null, false)).toMatchObject({
      enabled: true,
      baseline_ratio: 2.5,
      baseline_days: 14,
    });
  });

  it('uses a one-hour window when a new ratio is entered and describes the sampling limit', () => {
    const fields = {
      ...emptyRuleFields(),
      name: 'Spike',
      locationMode: 'worldwide' as const,
      ratio: '3',
    };
    expect(ruleProblems(fields, context)).toEqual({});
    expect(ruleRequest(fields, scope)).toMatchObject({
      baseline_ratio: 3,
      baseline_days: 30,
      window_minutes: 60,
      threshold: 1,
    });
    const summary = ruleSummary(fields, {
      countryName: (id) => id,
      templateName: (id) => id,
      bbox: undefined,
    });
    expect(summary).toContainEqual({ label: 'Time window', text: 'The last 1 hour' });
    expect(summary.find((row) => row.label === 'Baseline ratio')?.text).toContain(
      '168 sampled hours',
    );
  });

  it('clears the ratio explicitly while retaining a non-default baseline window', () => {
    const fields = { ...ruleFieldsFromIndicator(ratioRule), ratio: '', window: '360' };
    expect(ruleRequest(fields, scope)).toMatchObject({
      baseline_ratio: null,
      baseline_days: 14,
      window_minutes: 360,
    });
  });

  it.each(['1', '0', '101', 'NaN', 'Infinity', ' '])('rejects invalid ratio %s', (ratio) => {
    const fields = { ...ruleFieldsFromIndicator(ratioRule), ratio };
    expect(ruleProblems(fields, context).baseline_ratio).toBeDefined();
  });

  it.each(['6', '31', '7.5', ''])('rejects invalid baseline day count %s', (baselineDays) => {
    const fields = { ...ruleFieldsFromIndicator(ratioRule), baselineDays };
    expect(ruleProblems(fields, context).baseline_days).toBeDefined();
  });

  it.each(['1.001', '100'])('accepts supported ratio %s without rounding it', (ratio) => {
    const fields = { ...ruleFieldsFromIndicator(ratioRule), ratio };
    expect(ruleProblems(fields, context)).toEqual({});
    expect(ruleRequest(fields, scope).baseline_ratio).toBe(Number(ratio));
  });
});
