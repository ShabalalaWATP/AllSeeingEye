import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useMapNewsFeed } from './useMapNewsFeed';

const article = liveEvent({ category: 'news', country_iso: 'GB' });
function deferred() {
  let resolve!: (items: LiveEvent[]) => void;
  const promise = new Promise<LiveEvent[]>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
beforeEach(() => {
  useEventsStore.getState().reset();
  applySession('user');
});

it('does not resurrect an explicit removal received before the snapshot response', async () => {
  const pending = deferred();
  vi.spyOn(api, 'fetchEvents').mockReturnValue(pending.promise);
  const { result } = renderHook(() => useMapNewsFeed(null, null));
  act(() => useEventsStore.getState().applyExpire([article.id]));
  await act(() => {
    pending.resolve([article]);
    return Promise.resolve();
  });
  expect(result.current.data?.items).toEqual([]);
});

it('keeps an out-of-viewport correction through a stale background response', async () => {
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([article]);
  const { result } = renderHook(() => useMapNewsFeed(null, null));
  await waitFor(() => expect(result.current.data?.items).toEqual([article]));
  const pending = deferred();
  fetch.mockReturnValueOnce(pending.promise);
  let refreshing!: Promise<void>;
  act(() => {
    refreshing = result.current.refresh();
  });
  const correction = { ...article, title: 'New evidence', observed_at: '2026-09-21T12:00:00Z' };
  act(() => {
    useEventsStore.getState().setCoverageBounds([-1, -1, 1, 1]);
    useEventsStore.getState().applyUpsert([correction]);
  });
  expect(useEventsStore.getState().byId[article.id]).toBeUndefined();
  expect(result.current.data?.items).toEqual([correction]);
  await act(async () => {
    pending.resolve([article]);
    await refreshing;
  });
  expect(result.current.data?.items).toEqual([correction]);
});

it.each(['country', 'time', 'access', 'account'] as const)(
  'discards a superseded snapshot and its removal journal on %s changes',
  async (change) => {
    const previous = deferred();
    const current = deferred();
    const fetch = vi
      .spyOn(api, 'fetchEvents')
      .mockReturnValueOnce(previous.promise)
      .mockReturnValue(current.promise);
    const { result, rerender } = renderHook(
      ({ country, hours }) => useMapNewsFeed(country, hours),
      { initialProps: { country: 'GB', hours: 24 } },
    );
    act(() => useEventsStore.getState().applyExpire([article.id]));
    act(() => {
      if (change === 'country') rerender({ country: 'FR', hours: 24 });
      if (change === 'time') rerender({ country: 'GB', hours: 48 });
      if (change === 'access') invalidateWorkspaceAccess();
      if (change === 'account') {
        applySession('anonymous');
        applySession('user');
      }
    });
    expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
    await act(() => {
      previous.resolve([article]);
      return Promise.resolve();
    });
    expect(result.current.data).toBeNull();
    const fresh = { ...article, country_iso: change === 'country' ? 'FR' : 'GB' };
    await act(() => {
      current.resolve([fresh]);
      return Promise.resolve();
    });
    expect(result.current.data?.items).toEqual([fresh]);
  },
);

it('drops the accepted snapshot and starts a fresh read when the live mirror resets', async () => {
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([article]);
  const { result } = renderHook(() => useMapNewsFeed(null, null));
  await waitFor(() => expect(result.current.data?.items).toEqual([article]));
  const pending = deferred();
  fetch.mockReturnValue(pending.promise);
  act(() => useEventsStore.getState().reset());
  expect(result.current.data).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(2);
  await act(() => {
    pending.resolve([]);
    return Promise.resolve();
  });
  expect(result.current.data?.items).toEqual([]);
});

it('keeps accepted page identity stable during unrelated rerenders and stream updates', async () => {
  vi.spyOn(api, 'fetchEvents').mockResolvedValue([article]);
  const { result, rerender } = renderHook(() => useMapNewsFeed(null, null));
  await waitFor(() => expect(result.current.data?.items).toEqual([article]));
  const page = result.current.data;
  rerender();
  act(() =>
    useEventsStore.getState().applyUpsert([liveEvent({ id: 'unrelated', category: 'aviation' })]),
  );
  expect(result.current.data).toBe(page);
});
