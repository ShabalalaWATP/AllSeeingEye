import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/trackers';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { conflictCard } from '@/test/fixtures.trackers';
import { useConflictRegions } from './useConflictRegions';

afterEach(() => vi.restoreAllMocks());

it('fetches only when enabled, aborts obsolete snapshots and never polls in the background', async () => {
  applySession('user');
  let resolve!: (cards: api.ConflictCard[]) => void;
  const fetch = vi.spyOn(api, 'fetchConflictBoard').mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const view = renderHook(({ enabled }) => useConflictRegions(enabled, null), {
    initialProps: { enabled: false },
  });
  expect(fetch).not.toHaveBeenCalled();
  view.rerender({ enabled: true });
  expect(view.result.current.loading).toBe(true);
  const signal = fetch.mock.calls[0]![0]!;
  view.rerender({ enabled: false });
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve([conflictCard]);
    await Promise.resolve();
  });
  expect(view.result.current.filtered).toEqual([]);
  fetch.mockResolvedValue([conflictCard]);
  view.rerender({ enabled: true });
  await waitFor(() => expect(view.result.current.filtered).toHaveLength(1));
  vi.useFakeTimers();
  await act(() => vi.advanceTimersByTimeAsync(15 * 60_000));
  expect(fetch).toHaveBeenCalledTimes(2);
  vi.useRealTimers();
  view.unmount();
  expect(fetch.mock.calls[1]![0]!.aborted).toBe(true);
});

it('handles errors, manual refresh, filters and selection dismissal without reviving highlights', async () => {
  applySession('user');
  const fetch = vi
    .spyOn(api, 'fetchConflictBoard')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue([conflictCard]);
  const view = renderHook(({ country, enabled }) => useConflictRegions(enabled, country), {
    initialProps: { country: null as string | null, enabled: true },
  });
  await waitFor(() => expect(view.result.current.error).toBe(true));
  act(() => view.result.current.retry());
  await waitFor(() => expect(view.result.current.filtered).toHaveLength(1));
  const region = view.result.current.filtered[0]!;
  expect(view.result.current.fetchedAt).not.toBeNull();
  act(() => view.result.current.select(region));
  expect(view.result.current.selected).toEqual(region);
  act(() => view.result.current.setQuery('missing'));
  expect(view.result.current.selected).toBeNull();
  act(() => view.result.current.setQuery(''));
  expect(view.result.current.selected).toBeNull();
  act(() => {
    view.result.current.select(region);
    view.result.current.setShowRegions(false);
  });
  expect(view.result.current.selected).toBeNull();
  act(() => view.result.current.setShowRegions(true));
  act(() => view.result.current.select(region));
  view.rerender({ country: 'GB', enabled: true });
  expect(view.result.current.selected).toBeNull();
  view.rerender({ country: null, enabled: true });
  act(() => view.result.current.setStatus('tension'));
  expect(view.result.current.filtered).toEqual([]);
  act(() => view.result.current.setStatus('all'));
  act(() => view.result.current.select(region));
  view.rerender({ country: null, enabled: false });
  view.rerender({ country: null, enabled: true });
  expect(view.result.current.selected).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(3);
});

it('immediately masks and aborts data when account or workspace access changes', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchConflictBoard').mockResolvedValue([conflictCard]);
  const view = renderHook(() => useConflictRegions(true, null));
  await waitFor(() => expect(view.result.current.filtered).toHaveLength(1));
  act(() => view.result.current.select(view.result.current.filtered[0]!));
  fetch.mockReturnValue(new Promise(() => undefined));
  act(() => invalidateWorkspaceAccess());
  expect(view.result.current.filtered).toEqual([]);
  expect(view.result.current.selected).toBeNull();
  expect(fetch.mock.calls[0]![0]!.aborted).toBe(true);
  act(() => applySession('anonymous'));
  expect(fetch.mock.calls[1]![0]!.aborted).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
});
