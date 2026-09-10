import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures.events';
import { useContextEvents } from './useContextEvents';

const SOURCES = ['noaa_swpc_scales', 'swpc_kp', 'noaa_swpc_alerts'];
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it('loads separate bounded source snapshots without bbox, streams or polling', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([liveEvent({ point: null })]);
  const view = renderHook(() => useContextEvents(SOURCES));
  await waitFor(() => expect(view.result.current.loading).toBe(false));
  expect(fetch.mock.calls.map(([query]) => query)).toEqual(
    SOURCES.map((source) => ({ sources: [source], limit: 33 })),
  );
  expect(view.result.current.events).toHaveLength(3);
  vi.useFakeTimers();
  await act(() => vi.advanceTimersByTimeAsync(60 * 60_000));
  expect(fetch).toHaveBeenCalledTimes(3);
  view.unmount();
  expect(fetch.mock.calls.every(([, signal]) => signal?.aborted)).toBe(true);
});

it('keeps successful sources after partial errors and refreshes explicitly', async () => {
  applySession('user');
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue([]);
  const view = renderHook(() => useContextEvents(SOURCES));
  await waitFor(() => expect(view.result.current.failures).toBe(1));
  expect(view.result.current.fetchedAt).toBeTruthy();
  act(() => view.result.current.refresh());
  await waitFor(() => expect(view.result.current.loading).toBe(false));
  expect(view.result.current.failures).toBe(0);
  expect(fetch).toHaveBeenCalledTimes(6);
});

it('caps returned data and cannot revive an old snapshot after signing back in', async () => {
  applySession('user');
  const sources = ['ioda_outages'];
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValue(Array.from({ length: 150 }, (_, index) => liveEvent({ id: String(index) })));
  const view = renderHook(() => useContextEvents(sources));
  await waitFor(() => expect(view.result.current.events).toHaveLength(100));
  fetch.mockReturnValue(new Promise(() => undefined));
  act(() => applySession('anonymous'));
  expect(view.result.current.events).toEqual([]);
  act(() => applySession('user'));
  expect(view.result.current.events).toEqual([]);
  expect(view.result.current.loading).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('discards a completed snapshot even when logout and the same login share a React batch', async () => {
  applySession('user');
  const sources = ['ioda_outages'];
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([liveEvent()]);
  const view = renderHook(() => useContextEvents(sources));
  await waitFor(() => expect(view.result.current.events).toHaveLength(1));
  fetch.mockReturnValue(new Promise(() => undefined));
  act(() => {
    applySession('anonymous');
    applySession('user');
  });
  expect(view.result.current.events).toEqual([]);
  expect(view.result.current.loading).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls[0]![1]!.aborted).toBe(true);
});

it('cancels and masks obsolete country, workspace and account snapshots', async () => {
  applySession('user');
  const sources = ['ioda_outages'];
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([liveEvent()]);
  const view = renderHook(({ country }) => useContextEvents(sources, country), {
    initialProps: { country: 'GB' },
  });
  await waitFor(() => expect(view.result.current.events).toHaveLength(1));
  let resolve!: (events: LiveEvent[]) => void;
  fetch.mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  view.rerender({ country: 'US' });
  expect(view.result.current.events).toEqual([]);
  expect(fetch.mock.calls[0]![1]!.aborted).toBe(true);
  const oldResolve = resolve;
  act(() => invalidateWorkspaceAccess());
  expect(fetch.mock.calls[1]![1]!.aborted).toBe(true);
  await act(async () => {
    oldResolve([liveEvent()]);
    await Promise.resolve();
  });
  expect(view.result.current.events).toEqual([]);
  act(() => applySession('anonymous'));
  expect(fetch.mock.calls[2]![1]!.aborted).toBe(true);
  await act(async () => {
    resolve([liveEvent()]);
    await Promise.resolve();
  });
  expect(view.result.current.events).toEqual([]);
  expect(view.result.current.loading).toBe(false);
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(fetch.mock.calls[1]![0]).toEqual({ sources: ['ioda_outages'], limit: 100, country: 'US' });
});
