import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { applySession } from '@/test/render';
import { useJobPolling } from './useJobPolling';

interface Summary {
  running: boolean;
}

const running = (item: Summary) => item.running;

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it('reads active jobs every five seconds and idle jobs every thirty seconds', async () => {
  applySession('user');
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi
    .fn((_signal: AbortSignal): Promise<Summary> => Promise.resolve({ running: false }))
    .mockResolvedValueOnce({ running: true });
  renderHook(() => useJobPolling(read, running));
  await act(async () => Promise.resolve());
  expect(read).toHaveBeenCalledTimes(1);
  await act(async () => vi.advanceTimersByTimeAsync(4_999));
  expect(read).toHaveBeenCalledTimes(1);
  await act(async () => vi.advanceTimersByTimeAsync(1));
  expect(read).toHaveBeenCalledTimes(2);
  await act(async () => vi.advanceTimersByTimeAsync(29_999));
  expect(read).toHaveBeenCalledTimes(2);
  await act(async () => vi.advanceTimersByTimeAsync(1));
  expect(read).toHaveBeenCalledTimes(3);
});

it('pauses while hidden, resumes on visibility and cancels on unmount', async () => {
  applySession('user');
  const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi.fn((_signal: AbortSignal): Promise<Summary> =>
    Promise.resolve({ running: true }),
  );
  const { unmount } = renderHook(() => useJobPolling(read, running));
  await act(async () => Promise.resolve());
  visibility.mockReturnValue('hidden');
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'));
    await Promise.resolve();
  });
  await act(async () => vi.advanceTimersByTimeAsync(60_000));
  expect(read).toHaveBeenCalledTimes(1);
  visibility.mockReturnValue('visible');
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'));
    await Promise.resolve();
  });
  expect(read).toHaveBeenCalledTimes(2);
  unmount();
  await act(async () => vi.advanceTimersByTimeAsync(60_000));
  expect(read).toHaveBeenCalledTimes(2);
});

it('retains the previous job on transient failure and backs off before retry', async () => {
  applySession('user');
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi
    .fn((_signal: AbortSignal): Promise<Summary> => Promise.resolve({ running: true }))
    .mockResolvedValueOnce({ running: true })
    .mockRejectedValueOnce(new ApiError(503, 'unavailable', 'Try again later.'));
  const { result } = renderHook(() => useJobPolling(read, running));
  await act(async () => Promise.resolve());
  expect(result.current.data).toEqual({ running: true });
  await act(async () => vi.advanceTimersByTimeAsync(5_000));
  expect(result.current.data).toEqual({ running: true });
  expect(result.current.error?.status).toBe(503);
  await act(async () => vi.advanceTimersByTimeAsync(9_999));
  expect(read).toHaveBeenCalledTimes(2);
  await act(async () => vi.advanceTimersByTimeAsync(1));
  expect(read).toHaveBeenCalledTimes(3);
  expect(result.current.error).toBeNull();
  expect(result.current.data).toEqual({ running: true });
});

it('discards stale private results and stops polling after permission denial', async () => {
  applySession('user');
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi
    .fn((_signal: AbortSignal): Promise<Summary> => Promise.resolve({ running: true }))
    .mockResolvedValueOnce({ running: true })
    .mockRejectedValueOnce(new ApiError(403, 'forbidden', 'Access changed.'));
  const { result } = renderHook(() => useJobPolling(read, running));
  await act(async () => Promise.resolve());
  expect(result.current.data).toEqual({ running: true });
  await act(async () => vi.advanceTimersByTimeAsync(5_000));
  expect(result.current.data).toBeNull();
  expect(result.current.error?.status).toBe(403);
  await act(async () => vi.advanceTimersByTimeAsync(60_000));
  expect(read).toHaveBeenCalledTimes(2);
});
