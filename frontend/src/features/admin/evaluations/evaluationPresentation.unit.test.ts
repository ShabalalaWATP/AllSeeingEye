import { describe, expect, it } from 'vitest';

import type { EvaluationRun } from '@/lib/api/evaluations';
import { llmProfiles } from '@/test/fixtures';

import {
  assessmentProfiles,
  describeRun,
  estimateCalls,
  formatCheck,
  formatTokens,
  isRatioCheck,
  parseCallCap,
  suggestedCallCap,
} from './evaluationPresentation';

const base = {
  status: 'running',
  stop_reason: null,
  cancel_requested: false,
} as const;

function state(overrides: Partial<EvaluationRun>): EvaluationRun {
  return { ...base, ...overrides } as EvaluationRun;
}

describe('evaluation presentation', () => {
  it('estimates calls and suggests a bounded cap', () => {
    expect(estimateCalls(3, 4)).toBe(12);
    expect(estimateCalls(-1, 4)).toBe(0);
    expect(suggestedCallCap(0, 4, 200)).toBe(1);
    expect(suggestedCallCap(60, 4, 200)).toBe(200);
  });

  it('accepts only whole caps within range', () => {
    expect(parseCallCap(' 12 ', 200)).toBe(12);
    expect(parseCallCap('0', 200)).toBeNull();
    expect(parseCallCap('201', 200)).toBeNull();
    expect(parseCallCap('1.5', 200)).toBeNull();
    expect(parseCallCap('', 200)).toBeNull();
  });

  it('keeps only assessment connections', () => {
    const embeddings = { ...llmProfiles[0]!, id: 'e', roles: ['embeddings' as const] };
    expect(assessmentProfiles([llmProfiles[0]!, embeddings]).map((item) => item.id)).toEqual([
      llmProfiles[0]!.id,
    ]);
  });

  it('describes every run state with text, not colour alone', () => {
    expect(describeRun(state({}))).toEqual({ tone: 'info', label: 'Running' });
    expect(describeRun(state({ cancel_requested: true })).label).toBe('Cancelling');
    expect(describeRun(state({ status: 'completed' })).tone).toBe('good');
    expect(describeRun(state({ status: 'cancelled' })).label).toBe('Cancelled');
    expect(describeRun(state({ status: 'stopped', stop_reason: 'call_cap' })).label).toBe(
      'Stopped at the call cap',
    );
    expect(describeRun(state({ status: 'stopped' })).label).toBe('Stopped');
  });

  it('formats structural checks and token counts', () => {
    expect(formatCheck(0.25, true)).toBe('25%');
    expect(formatCheck(3, false)).toBe('3');
    expect(formatCheck(null, true)).toBe('Not applicable');
    expect(formatCheck(undefined, false)).toBe('Not applicable');
    expect(formatCheck(true, false)).toBe('Yes');
    expect(formatCheck(false, false)).toBe('No');
    expect(isRatioCheck('required_evidence_cited_recall')).toBe(true);
    expect(isRatioCheck('validation_errors')).toBe(false);
    expect(formatTokens(null)).toBe('Not reported');
    expect(formatTokens(1200)).toBe('1,200');
  });
});
