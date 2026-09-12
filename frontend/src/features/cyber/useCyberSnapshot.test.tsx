import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import * as cyberApi from '@/lib/api/cyber';
import type { CyberDays, CyberSnapshot } from '@/lib/api/cyber';
import { ApiError } from '@/lib/api/errors';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { cyberSnapshot } from '@/test/fixtures.cyber';
import { useCyberSnapshot } from './useCyberSnapshot';

const busy = (seconds: number | null = 1) =>
  new ApiError(429, 'rate_limited', 'Snapshot preparation is busy.', {}, seconds);

function deferred() {
  let resolve!: (value: CyberSnapshot) => void;
  const promise = new Promise<CyberSnapshot>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function advance(milliseconds = 0) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  useAuthStore.getState().setSession(tokenFor(plainUser));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it('forwards an already aborted snapshot signal without sending an HTTP request', async () => {
  const fetch = vi.spyOn(window, 'fetch');
  const controller = new AbortController();
  controller.abort();
  await expect(cyberApi.fetchCyberSnapshot(2, controller.signal)).rejects.toMatchObject({
    name: 'AbortError',
  });
  expect(fetch).not.toHaveBeenCalled();
});

it('recovers the new period after a rapid switch encounters the preparation limit', async () => {
  const old = deferred();
  const fetch = vi
    .spyOn(cyberApi, 'fetchCyberSnapshot')
    .mockReturnValueOnce(old.promise)
    .mockRejectedValueOnce(busy(2))
    .mockResolvedValue(cyberSnapshot(14));
  const { result, rerender } = renderHook(({ days }) => useCyberSnapshot(days), {
    initialProps: { days: 2 as CyberDays },
  });
  const oldSignal = fetch.mock.calls[0]![1]!;
  rerender({ days: 14 });
  expect(oldSignal.aborted).toBe(true);
  expect(result.current.data).toBeNull();
  await advance();
  expect(result.current.loading).toBe(true);
  expect(result.current.error).toBeNull();
  await advance(1999);
  expect(fetch).toHaveBeenCalledTimes(2);
  await advance(1);
  expect(fetch).toHaveBeenLastCalledWith(14, expect.any(AbortSignal));
  expect(result.current.data?.window_days).toBe(14);
  expect(result.current.loading).toBe(false);
  await act(async () => {
    old.resolve(cyberSnapshot(2));
    await old.promise;
  });
  expect(result.current.data?.window_days).toBe(14);
});

it('cancels a previous period retry timer when another period is selected', async () => {
  const fetch = vi
    .spyOn(cyberApi, 'fetchCyberSnapshot')
    .mockRejectedValueOnce(busy(5))
    .mockResolvedValue(cyberSnapshot(7));
  const { result, rerender } = renderHook(({ days }) => useCyberSnapshot(days), {
    initialProps: { days: 2 as CyberDays },
  });
  await advance();
  expect(vi.getTimerCount()).toBe(1);
  rerender({ days: 7 });
  await advance();
  expect(fetch.mock.calls[0]![1]!.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
  await advance(10_000);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(result.current.data?.window_days).toBe(7);
});

it.each(['access', 'identity'] as const)(
  'aborts pending retry work on %s changes and only loads under current authority',
  async (change) => {
    const current = { ...cyberSnapshot(2), coverage_note: 'Current authority result' };
    const fetch = vi
      .spyOn(cyberApi, 'fetchCyberSnapshot')
      .mockRejectedValueOnce(busy(5))
      .mockResolvedValue(current);
    const { result } = renderHook(() => useCyberSnapshot(2));
    await advance();
    const oldSignal = fetch.mock.calls[0]![1]!;
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(oldSignal.aborted).toBe(true);
    await advance();
    expect(result.current.data).toEqual(current);
    expect(vi.getTimerCount()).toBe(0);
    await advance(10_000);
    expect(fetch).toHaveBeenCalledTimes(2);
  },
);

it('cancels the pending retry timer on unmount', async () => {
  const fetch = vi.spyOn(cyberApi, 'fetchCyberSnapshot').mockRejectedValue(busy(1));
  const { unmount } = renderHook(() => useCyberSnapshot(2));
  await advance();
  expect(vi.getTimerCount()).toBe(1);
  unmount();
  expect(fetch.mock.calls[0]![1]!.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
  await advance(10_000);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('aborts an in-flight snapshot request on unmount', async () => {
  const pending = deferred();
  const fetch = vi.spyOn(cyberApi, 'fetchCyberSnapshot').mockReturnValue(pending.promise);
  const { unmount } = renderHook(() => useCyberSnapshot(2));
  const signal = fetch.mock.calls[0]![1]!;
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    pending.resolve(cyberSnapshot());
    await pending.promise;
  });
  expect(vi.getTimerCount()).toBe(0);
});

it('stops after four automatic retries and leaves the normal reload action available', async () => {
  const fetch = vi.spyOn(cyberApi, 'fetchCyberSnapshot').mockRejectedValue(busy());
  const { result } = renderHook(() => useCyberSnapshot(2));
  await advance(4000);
  expect(fetch).toHaveBeenCalledTimes(5);
  expect(result.current.error?.status).toBe(429);
  expect(result.current.loading).toBe(false);
  expect(vi.getTimerCount()).toBe(0);
  await advance(60_000);
  expect(fetch).toHaveBeenCalledTimes(5);
  fetch.mockResolvedValue(cyberSnapshot());
  await act(async () => {
    await result.current.reload();
  });
  expect(result.current.error).toBeNull();
  expect(result.current.data?.window_days).toBe(2);
});

it.each([new ApiError(403, 'forbidden', 'Access removed.'), busy(60)])(
  'does not automatically retry a forbidden request or shorten a long server cooldown',
  async (error) => {
    const fetch = vi.spyOn(cyberApi, 'fetchCyberSnapshot').mockRejectedValue(error);
    const { result } = renderHook(() => useCyberSnapshot(2));
    await advance();
    expect(result.current.error).toBe(error);
    expect(result.current.loading).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    await advance(60_000);
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

it.each([
  [null, 1000],
  [0, 250],
] as const)('uses a bounded delay for Retry-After %s', async (seconds, delay) => {
  const fetch = vi
    .spyOn(cyberApi, 'fetchCyberSnapshot')
    .mockRejectedValueOnce(busy(seconds))
    .mockResolvedValue(cyberSnapshot());
  const { result } = renderHook(() => useCyberSnapshot(2));
  await advance(delay - 1);
  expect(fetch).toHaveBeenCalledTimes(1);
  await advance(1);
  expect(result.current.data?.window_days).toBe(2);
});
