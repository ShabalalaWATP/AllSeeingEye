import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import { ApiError } from '@/lib/api/errors';
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

it.each([SOURCES, ['ioda_outages', 'ioda_outage_events', 'cloudflare_radar_outages']])(
  'loads every context source while leaving room for another panel: %s',
  async (...sources) => {
    applySession('user');
    let active = 1; // Another map panel occupies one of the server's two user slots.
    let peak = active;
    const fetch = vi.spyOn(api, 'fetchEvents').mockImplementation(async (query) => {
      if (active >= 2) throw new ApiError(429, 'rate_limited', 'Too many reads.');
      active += 1;
      peak = Math.max(peak, active);
      try {
        await new Promise<void>((resolve) => queueMicrotask(resolve));
        const source = query?.sources?.[0];
        if (!source) throw new Error('Expected a source-specific context query.');
        return [liveEvent({ id: source, source_id: source })];
      } finally {
        active -= 1;
      }
    });
    const view = renderHook(() => useContextEvents(sources));
    await waitFor(() => expect(view.result.current.loading).toBe(false));
    expect(view.result.current.failures).toBe(0);
    expect(view.result.current.events.map((event) => event.source_id)).toEqual(sources);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(peak).toBe(2);
  },
);

it.each(['resolve', 'reject'] as const)(
  'stops queued sources when an in-flight request settles after logout (%s)',
  async (outcome) => {
    applySession('user');
    let release!: (events: LiveEvent[]) => void;
    let reject!: (error: Error) => void;
    const pending = new Promise<LiveEvent[]>((resolve, fail) => {
      release = resolve;
      reject = fail;
    });
    const fetch = vi.spyOn(api, 'fetchEvents').mockReturnValue(pending);
    const view = renderHook(() => useContextEvents(SOURCES));
    expect(fetch).toHaveBeenCalledTimes(1);
    act(() => applySession('anonymous'));
    await act(async () => {
      if (outcome === 'resolve') release([liveEvent()]);
      else reject(new Error('late failure'));
      await Promise.resolve();
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
    expect(view.result.current.events).toEqual([]);
    expect(view.result.current.failures).toBe(0);
    expect(view.result.current.loading).toBe(false);
  },
);

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

it('does not fetch a Network snapshot until its panel is enabled', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([liveEvent()]);
  const sources = ['ioda_outages'];
  const view = renderHook(({ enabled }) => useContextEvents(sources, null, enabled), {
    initialProps: { enabled: false },
  });
  expect(view.result.current.loading).toBe(false);
  expect(fetch).not.toHaveBeenCalled();
  view.rerender({ enabled: true });
  await waitFor(() => expect(view.result.current.events).toHaveLength(1));
  expect(fetch).toHaveBeenCalledTimes(1);
  view.rerender({ enabled: false });
  expect(view.result.current.events).toEqual([]);
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
