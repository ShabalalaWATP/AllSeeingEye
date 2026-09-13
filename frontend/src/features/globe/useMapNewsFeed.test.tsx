import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';
import { useMapNewsFeed } from './useMapNewsFeed';

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
const record = liveEvent({ category: 'news' });

it('loads a bounded geographic snapshot only while enabled and authenticated', async () => {
  applySession('user');
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValue(Array.from({ length: 301 }, () => record));
  const { result, rerender } = renderHook(
    ({ enabled }) => useMapNewsFeed('GB', 48, enabled, true),
    { initialProps: { enabled: false } },
  );
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch).not.toHaveBeenCalled();
  rerender({ enabled: true });
  await waitFor(() => expect(result.current.data?.items).toHaveLength(300));
  expect(fetch).toHaveBeenCalledWith(
    {
      categories: ['news', 'political', 'humanitarian', 'economic', 'social'],
      limit: 300,
      country: 'GB',
      since: expect.any(String),
      sampling: 'geographic',
      timeBasis: 'map_record_time',
    },
    expect.any(AbortSignal),
  );
  act(() => useAuthStore.getState().clearSession());
  await waitFor(() => expect(result.current.data?.items).toEqual([]));
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
});

it('refreshes after completion without overlapping slow requests and cancels when switched off', async () => {
  applySession('user');
  vi.useFakeTimers();
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([record]);
  const { result, rerender } = renderHook(
    ({ enabled }) => useMapNewsFeed(null, null, enabled, true),
    { initialProps: { enabled: true } },
  );
  await act(() => Promise.resolve());
  expect(result.current.data?.items).toEqual([record]);
  let finish!: (events: LiveEvent[]) => void;
  fetch.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
  });
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(result.current.data?.items).toEqual([record]);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(180_000);
  });
  expect(fetch).toHaveBeenCalledTimes(2);
  rerender({ enabled: false });
  expect(fetch.mock.calls[1]?.[1]?.aborted).toBe(true);
  await act(() => {
    finish([record]);
    return Promise.resolve();
  });
  expect(result.current.data?.items).toEqual([]);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
  });
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('keeps headline queries on publication time and surfaces errors', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchEvents').mockRejectedValue(new Error('offline'));
  const { result } = renderHook(() => useMapNewsFeed(null, 24));
  await waitFor(() => expect(result.current.error).toBeTruthy());
  expect(result.current.data).toBeNull();
  expect(fetch.mock.calls[0]?.[0]).not.toHaveProperty('timeBasis');
  expect(fetch.mock.calls[0]?.[0]).not.toHaveProperty('sampling');
});
