import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as evaluations from '@/lib/api/evaluations';
import type { EvaluationRun, EvaluationStart } from '@/lib/api/evaluations';
import * as llm from '@/lib/api/llm';
import * as downloads from '@/lib/downloadBinary';
import { llmProfiles } from '@/test/fixtures';

import { useEvaluations } from './useEvaluations';

const history: EvaluationRun = {
  id: '99999999-9999-4999-8999-999999999999',
  profile_id: llmProfiles[0]!.id,
  profile_name: 'Local Llama',
  model: 'llama3.1:8b',
  status: 'completed',
  stop_reason: null,
  cancel_requested: false,
  case_ids: ['date_pitfall'],
  case_fingerprints: { date_pitfall: 'b'.repeat(64) },
  max_calls: 4,
  estimated_calls: 4,
  calls_reserved: 4,
  calls_failed: 0,
  prompt_tokens: null,
  completion_tokens: null,
  results: [],
  has_artefact: true,
  created_at: '2026-10-01T09:00:00Z',
  finished_at: '2026-10-01T09:05:00Z',
  notice: 'Structural checks, not accuracy.',
};
const body: EvaluationStart = {
  profile_id: history.profile_id,
  case_ids: history.case_ids,
  max_calls: 4,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.spyOn(evaluations, 'fetchEvaluationCatalogue').mockResolvedValue({
    cases: [],
    calls_per_case: 4,
    max_calls: 200,
    max_cases: 40,
    estimate_notice: 'Estimated calls only.',
    result_notice: history.notice,
  });
  vi.spyOn(llm, 'fetchLlmProfiles').mockResolvedValue({
    items: llmProfiles,
    encryption_available: true,
  });
  vi.spyOn(evaluations, 'fetchEvaluationRuns').mockResolvedValue([history]);
  vi.spyOn(downloads, 'saveBinaryFile').mockImplementation(() => undefined);
});

it('keeps history on a failed start and clears the error when an explicit retry succeeds', async () => {
  const unavailable = new ApiError(503, 'unavailable', 'The connection is unavailable.');
  const started: EvaluationRun = {
    ...history,
    id: '88888888-8888-4888-8888-888888888888',
    status: 'running',
  };
  const start = vi
    .spyOn(evaluations, 'startEvaluationRun')
    .mockRejectedValueOnce(unavailable)
    .mockResolvedValue(started);
  const { result } = renderHook(() => useEvaluations());
  await waitFor(() => expect(result.current.loading).toBe(false));
  await act(async () => expect(await result.current.start(body)).toBe(false));
  expect(result.current.runs).toEqual([history]);
  expect(result.current.error).toBe(unavailable);
  expect(result.current.busy).toBe(false);
  await act(async () => expect(await result.current.start(body)).toBe(true));
  expect(start).toHaveBeenCalledTimes(2);
  expect(start).toHaveBeenLastCalledWith(body);
  expect(result.current.runs).toEqual([started, history]);
  expect(result.current.error).toBeNull();
});

it('keeps history visible while a start is pending, then prepends the accepted run', async () => {
  const pending = deferred<EvaluationRun>();
  vi.spyOn(evaluations, 'startEvaluationRun').mockReturnValue(pending.promise);
  const { result } = renderHook(() => useEvaluations());
  await waitFor(() => expect(result.current.loading).toBe(false));
  let action!: Promise<boolean>;
  act(() => {
    action = result.current.start(body);
  });
  expect(result.current.busy).toBe(true);
  expect(result.current.runs).toEqual([history]);
  const started: EvaluationRun = {
    ...history,
    id: '88888888-8888-4888-8888-888888888888',
    status: 'running',
  };
  await act(async () => {
    pending.resolve(started);
    expect(await action).toBe(true);
  });
  expect(result.current.runs).toEqual([started, history]);
  expect(result.current.busy).toBe(false);
});

it('preserves a running job on cancellation failure and replaces only that job after retry', async () => {
  const running: EvaluationRun = {
    ...history,
    id: '88888888-8888-4888-8888-888888888888',
    status: 'running',
  };
  const cancelled: EvaluationRun = { ...running, status: 'cancelled', cancel_requested: true };
  const denied = new ApiError(403, 'forbidden', 'Cancellation is not currently permitted.');
  const pending = deferred<EvaluationRun>();
  vi.mocked(evaluations.fetchEvaluationRuns).mockResolvedValue([running, history]);
  const cancel = vi
    .spyOn(evaluations, 'cancelEvaluationRun')
    .mockRejectedValueOnce(denied)
    .mockReturnValue(pending.promise);
  const { result } = renderHook(() => useEvaluations());
  await waitFor(() => expect(result.current.loading).toBe(false));
  await act(() => result.current.cancel(running.id));
  expect(result.current.runs).toEqual([running, history]);
  expect(result.current.error).toBe(denied);
  expect(result.current.busy).toBe(false);
  let action!: Promise<void>;
  act(() => {
    action = result.current.cancel(running.id);
  });
  expect(result.current.busy).toBe(true);
  await act(async () => {
    pending.resolve(cancelled);
    await action;
  });
  expect(cancel).toHaveBeenLastCalledWith(running.id);
  expect(result.current.runs).toEqual([cancelled, history]);
  expect(result.current.error).toBeNull();
  expect(result.current.busy).toBe(false);
});

it.each(['review-template.zip', null])(
  'does not save a failed download and retries using the filename %s',
  async (filename) => {
    const unavailable = new ApiError(404, 'not_found', 'The artefact is no longer available.');
    const blob = new Blob(['synthetic review template'], { type: 'application/zip' });
    const pending = deferred<{ blob: Blob; filename: string | null }>();
    const download = vi
      .spyOn(evaluations, 'downloadEvaluationArtefact')
      .mockRejectedValueOnce(unavailable)
      .mockReturnValue(pending.promise);
    const { result } = renderHook(() => useEvaluations());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(() => result.current.download(history));
    expect(downloads.saveBinaryFile).not.toHaveBeenCalled();
    expect(result.current.error).toBe(unavailable);
    expect(result.current.busy).toBe(false);
    let action!: Promise<void>;
    act(() => {
      action = result.current.download(history);
    });
    expect(result.current.busy).toBe(true);
    await act(async () => {
      pending.resolve({ blob, filename });
      await action;
    });
    expect(download).toHaveBeenLastCalledWith(history.id);
    expect(downloads.saveBinaryFile).toHaveBeenCalledExactlyOnceWith(
      filename ?? `evaluation-${history.id}.zip`,
      blob,
    );
    expect(result.current.error).toBeNull();
    expect(result.current.busy).toBe(false);
    expect(result.current.runs).toEqual([history]);
  },
);

it('reports a local file-save failure without leaving the controls busy or exposing raw errors', async () => {
  vi.spyOn(evaluations, 'downloadEvaluationArtefact').mockResolvedValue({
    blob: new Blob(['synthetic result']),
    filename: 'evaluation.zip',
  });
  vi.mocked(downloads.saveBinaryFile).mockImplementation(() => {
    throw new Error('Private browser storage failure details');
  });
  const { result } = renderHook(() => useEvaluations());
  await waitFor(() => expect(result.current.loading).toBe(false));
  await act(() => result.current.download(history));
  expect(result.current.error?.code).toBe('unexpected_error');
  expect(result.current.error?.message).toBe('Something went wrong. Please try again.');
  expect(result.current.busy).toBe(false);
  expect(result.current.runs).toEqual([history]);
});
