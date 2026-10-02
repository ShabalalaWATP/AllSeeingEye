import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as evaluations from '@/lib/api/evaluations';
import type { EvaluationCatalogue, EvaluationRun } from '@/lib/api/evaluations';
import * as llm from '@/lib/api/llm';
import { llmProfiles } from '@/test/fixtures';

import { POLL_INTERVAL_MS, useEvaluations } from './useEvaluations';

const catalogue: EvaluationCatalogue = {
  cases: [],
  calls_per_case: 4,
  max_calls: 200,
  max_cases: 40,
  estimate_notice: 'Estimated calls only.',
  result_notice: 'Structural checks, not accuracy.',
};
const running: EvaluationRun = {
  id: '99999999-9999-4999-8999-999999999999',
  profile_id: llmProfiles[0]!.id,
  profile_name: 'Local Llama',
  model: 'llama3.1:8b',
  status: 'running',
  stop_reason: null,
  cancel_requested: false,
  case_ids: ['date_pitfall'],
  case_fingerprints: { date_pitfall: 'b'.repeat(64) },
  max_calls: 4,
  estimated_calls: 4,
  calls_reserved: 1,
  calls_failed: 0,
  prompt_tokens: null,
  completion_tokens: null,
  results: [],
  has_artefact: false,
  created_at: '2026-10-01T09:00:00Z',
  finished_at: null,
  notice: 'Structural checks, not accuracy.',
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

const advance = (milliseconds = 0) => act(() => vi.advanceTimersByTimeAsync(milliseconds));

beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(evaluations, 'fetchEvaluationCatalogue').mockResolvedValue(catalogue);
  vi.spyOn(llm, 'fetchLlmProfiles').mockResolvedValue({
    items: llmProfiles,
    encryption_available: true,
  });
  vi.spyOn(evaluations, 'fetchEvaluationRuns').mockResolvedValue([running]);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it('keeps the last progress after a failed poll, recovers and stops polling on completion', async () => {
  const unavailable = new ApiError(503, 'unavailable', 'Run progress is temporarily unavailable.');
  const completed: EvaluationRun = {
    ...running,
    status: 'completed',
    calls_reserved: 4,
    has_artefact: true,
    finished_at: '2026-10-01T09:05:00Z',
  };
  const fetch = vi
    .mocked(evaluations.fetchEvaluationRuns)
    .mockResolvedValueOnce([running])
    .mockRejectedValueOnce(unavailable)
    .mockResolvedValue([completed]);
  const { result } = renderHook(() => useEvaluations());
  await advance();
  expect(result.current.loading).toBe(false);
  await advance(POLL_INTERVAL_MS - 1);
  expect(fetch).toHaveBeenCalledTimes(1);
  await advance(1);
  expect(result.current.runs).toEqual([running]);
  expect(result.current.error).toBe(unavailable);
  await advance(POLL_INTERVAL_MS);
  expect(result.current.runs).toEqual([completed]);
  expect(result.current.busy).toBe(false);
  await advance(POLL_INTERVAL_MS * 3);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it('loads history without scheduling polls when no run is active', async () => {
  const completed: EvaluationRun = { ...running, status: 'completed' };
  vi.mocked(evaluations.fetchEvaluationRuns).mockResolvedValue([completed]);
  const { result } = renderHook(() => useEvaluations());
  await advance();
  expect(result.current.catalogue).toEqual(catalogue);
  expect(result.current.runs).toEqual([completed]);
  expect(result.current.profiles).toEqual(
    llmProfiles.filter((profile) => profile.roles.includes('assessment')),
  );
  await advance(POLL_INTERVAL_MS * 3);
  expect(evaluations.fetchEvaluationRuns).toHaveBeenCalledTimes(1);
});

it('ends loading on an initial failure without publishing a partial casebook or polling', async () => {
  const denied = new ApiError(403, 'forbidden', 'Administrator access is required.');
  vi.mocked(llm.fetchLlmProfiles).mockRejectedValue(denied);
  const { result } = renderHook(() => useEvaluations());
  expect(result.current.loading).toBe(true);
  await advance();
  expect(result.current.loading).toBe(false);
  expect(result.current.error).toBe(denied);
  expect(result.current.catalogue).toBeNull();
  expect(result.current.runs).toEqual([]);
  await advance(POLL_INTERVAL_MS * 3);
  expect(evaluations.fetchEvaluationRuns).toHaveBeenCalledTimes(1);
});

it.each(['resolve', 'reject'] as const)(
  'aborts initial requests on unmount and ignores their late %s outcome',
  async (outcome) => {
    const pending = deferred<EvaluationCatalogue>();
    vi.mocked(evaluations.fetchEvaluationCatalogue).mockReturnValue(pending.promise);
    const { result, unmount } = renderHook(() => useEvaluations());
    const catalogueSignal = vi.mocked(evaluations.fetchEvaluationCatalogue).mock.calls[0]![0]!;
    const runsSignal = vi.mocked(evaluations.fetchEvaluationRuns).mock.calls[0]![0]!;
    const initial = result.current;
    unmount();
    expect(catalogueSignal.aborted).toBe(true);
    expect(runsSignal.aborted).toBe(true);
    await act(async () => {
      if (outcome === 'resolve') pending.resolve(catalogue);
      else pending.reject(new Error('Late network failure'));
      await pending.promise.catch(() => undefined);
    });
    await advance(POLL_INTERVAL_MS * 3);
    expect(result.current).toBe(initial);
    expect(evaluations.fetchEvaluationRuns).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  },
);

it.each(['resolve', 'reject'] as const)(
  'disposes polling and ignores an in-flight poll that later %ss',
  async (outcome) => {
    const pending = deferred<EvaluationRun[]>();
    const fetch = vi
      .mocked(evaluations.fetchEvaluationRuns)
      .mockResolvedValueOnce([running])
      .mockReturnValue(pending.promise);
    const { result, unmount } = renderHook(() => useEvaluations());
    await advance();
    await advance(POLL_INTERVAL_MS);
    expect(fetch).toHaveBeenCalledTimes(2);
    const latest = result.current;
    unmount();
    await act(async () => {
      if (outcome === 'resolve') pending.resolve([{ ...running, status: 'completed' }]);
      else pending.reject(new Error('Late poll failure'));
      await pending.promise.catch(() => undefined);
    });
    await advance(POLL_INTERVAL_MS * 3);
    expect(result.current).toBe(latest);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
  },
);
