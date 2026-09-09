import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/aviation';
import { jamMap } from '@/test/fixtures.trackers';
import { useInterference } from './useInterference';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it('does not fetch while off, coalesces polling and ignores results after cancellation', async () => {
  vi.useFakeTimers();
  let resolve!: (value: api.JamMap) => void;
  const fetch = vi.spyOn(api, 'fetchJamMap').mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const view = renderHook(({ enabled }) => useInterference(enabled), {
    initialProps: { enabled: false },
  });
  expect(fetch).not.toHaveBeenCalled();
  view.rerender({ enabled: true });
  expect(view.result.current.loading).toBe(true);
  expect(fetch).toHaveBeenCalledOnce();
  await act(() => vi.advanceTimersByTimeAsync(10 * 60_000));
  expect(fetch).toHaveBeenCalledOnce();
  const signal = fetch.mock.calls[0]![0]!;
  view.rerender({ enabled: false });
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve(jamMap);
    await Promise.resolve();
  });
  expect(view.result.current.cells).toEqual([]);
  expect(view.result.current.receivedAt).toBeNull();
  expect(view.result.current.loading).toBe(false);
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it('timestamps successful snapshots and keeps that age on failure until manual recovery', async () => {
  vi.useFakeTimers();
  const started = Date.UTC(2026, 8, 9, 12);
  vi.setSystemTime(started);
  const fetch = vi
    .spyOn(api, 'fetchJamMap')
    .mockResolvedValueOnce(jamMap)
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ cells: [], updated_at: null });
  const view = renderHook(() => useInterference(true));
  await act(() => Promise.resolve());
  expect(view.result.current.receivedAt).toBe(started);
  await act(() => vi.advanceTimersByTimeAsync(5 * 60_000));
  expect(view.result.current.error).toBe('Something went wrong. Please try again.');
  expect(view.result.current.cells).toEqual(jamMap.cells);
  expect(view.result.current.receivedAt).toBe(started);
  await act(async () => {
    view.result.current.refresh();
    await Promise.resolve();
  });
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(view.result.current.receivedAt).toBe(started + 5 * 60_000);
  expect(view.result.current.error).toBeNull();
  expect(view.result.current.cells).toEqual([]);
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
