import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { setVisibility } from '@/test/env';
import { reportJob } from '@/test/reportJobFixture';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import type { ReportJob } from '@/lib/api/reportJobs';
import { useJobPolling } from './useJobPolling';
import { jobRunning } from './jobLabels';

afterEach(() => vi.useRealTimers());

it('polls only when visible, never overlaps requests and stops after a terminal result', async () => {
  vi.useFakeTimers();
  applySession('user');
  let release: (value: ReportJob) => void = () => undefined;
  const gate = new Promise<ReportJob>((resolve) => {
    release = resolve;
  });
  const loader = vi
    .fn<(signal: AbortSignal) => Promise<ReportJob>>()
    .mockResolvedValueOnce(reportJob())
    .mockReturnValueOnce(gate)
    .mockResolvedValue(reportJob({ status: 'completed', stage: 'completed' }));
  const view = renderHook(() => useJobPolling(loader, jobRunning));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3000);
  });
  expect(loader).toHaveBeenCalledTimes(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15000);
  });
  expect(loader).toHaveBeenCalledTimes(2);
  act(() => setVisibility('hidden'));
  expect(loader.mock.calls[1]?.[0].aborted).toBe(true);
  await act(async () => {
    release(reportJob());
    await gate;
    await vi.advanceTimersByTimeAsync(9000);
  });
  expect(loader).toHaveBeenCalledTimes(2);
  await act(async () => {
    setVisibility('visible');
    await Promise.resolve();
  });
  expect(view.result.current.data?.status).toBe('completed');
  await act(async () => {
    await vi.advanceTimersByTimeAsync(12000);
  });
  expect(loader).toHaveBeenCalledTimes(3);
  view.unmount();
});

it('clears old access data immediately and rejects a stale in-flight poll', async () => {
  vi.useFakeTimers();
  applySession('user');
  let release: (value: ReportJob) => void = () => undefined;
  const gate = new Promise<ReportJob>((resolve) => {
    release = resolve;
  });
  const loader = vi
    .fn<(signal: AbortSignal) => Promise<ReportJob>>()
    .mockResolvedValueOnce(reportJob({ title: 'Private initial view' }))
    .mockReturnValueOnce(gate)
    .mockResolvedValue(reportJob({ title: 'Fresh authorised view', status: 'paused' }));
  const view = renderHook(() => useJobPolling(loader, jobRunning));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3000);
  });
  expect(view.result.current.data?.title).toBe('Private initial view');
  act(() => invalidateWorkspaceAccess());
  expect(view.result.current.data).toBeNull();
  expect(loader.mock.calls[1]?.[0].aborted).toBe(true);
  await act(async () => {
    release(reportJob({ title: 'Stale private view' }));
    await gate;
  });
  expect(view.result.current.data?.title).toBe('Fresh authorised view');
});
