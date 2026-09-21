import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';
import { liveEvent, plainUser, USER_TOKEN } from '@/test/fixtures';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useDashboardEvents } from './useDashboardEvents';

const now = Date.parse('2026-09-20T12:00:00Z');
const article = liveEvent({
  id: 'supplemental-news',
  category: 'news',
  published_at: '2026-09-20T11:30:00Z',
});
const aircraft = liveEvent({ id: 'aircraft', category: 'aviation' });
let articles = [article];
beforeEach(() => {
  articles = [article];
  useAuthStore.setState({ status: 'authenticated', user: plainUser, accessToken: USER_TOKEN });
  useEventsStore.getState().reset();
  useEventsStore.setState({ hidden: [] });
  useEventsStore.getState().applyUpsert([aircraft]);
  server.use(
    http.get('/api/events', ({ request }) => {
      const items = new URL(request.url).searchParams.has('time_basis') ? articles : [aircraft];
      return HttpResponse.json({ items, count: items.length });
    }),
    http.get('/api/events/stats', () =>
      HttpResponse.json({
        total: 1,
        estimated_bytes: 1,
        budget_bytes: 1000,
        per_category: [{ category: 'aviation', count: 1, oldest: null, newest: null }],
      }),
    ),
  );
});
async function selectArticle() {
  const hook = renderHook(() => useDashboardEvents(now));
  await waitFor(() => expect(hook.result.current.quality.filtered).toContainEqual(article));
  expect(useEventsStore.getState().byId[article.id]).toBeUndefined();
  act(() => hook.result.current.select(article.id));
  expect(hook.result.current.selected?.id).toBe(article.id);
  return hook;
}
it('retains a supplemental marker selection through unrelated live changes and mirror snapshots', async () => {
  const { result } = await selectArticle();
  act(() =>
    useEventsStore
      .getState()
      .applyUpsert([liveEvent({ id: 'other-aircraft', category: 'aviation' })]),
  );
  expect(result.current.selected?.id).toBe(article.id);
  act(() => useEventsStore.getState().applyExpire(['other-aircraft']));
  expect(result.current.selected?.id).toBe(article.id);
  await act(() => useEventsStore.getState().load());
  expect(result.current.selected?.id).toBe(article.id);
});
it('clears explicit expiry even when the selected article exists only in a supplemental snapshot', async () => {
  const { result } = await selectArticle();
  act(() => useEventsStore.getState().applyExpire([article.id]));
  expect(result.current.selected).toBeNull();
  expect(result.current.quality.filtered.some((event) => event.id === article.id)).toBe(false);
});

it('keeps a newer live correction instead of the older news snapshot', async () => {
  const { result } = await selectArticle();
  const corrected = {
    ...article,
    title: 'Corrected location',
    observed_at: '2026-09-21T12:00:00Z',
  };
  act(() => useEventsStore.getState().applyUpsert([corrected]));
  expect(result.current.selected?.title).toBe(corrected.title);
  expect(result.current.newsSnapshot.data?.items[0]?.title).toBe(corrected.title);
});

it('does not retain a country-corrected article through its old snapshot', async () => {
  const { result } = await selectArticle();
  act(() => result.current.setCountry('DE'));
  await waitFor(() => expect(result.current.newsSnapshot.loading).toBe(false));
  act(() =>
    useEventsStore
      .getState()
      .applyUpsert([{ ...article, country_iso: 'FR', observed_at: '2026-09-21T12:00:00Z' }]),
  );
  expect(result.current.newsSnapshot.data?.items).toEqual([]);
});
it('clears selection when its owning snapshot removes the article and never revives it', async () => {
  const { result } = await selectArticle();
  articles = [];
  await act(() => result.current.newsSnapshot.refresh());
  expect(result.current.selected).toBeNull();
  articles = [article];
  await act(() => result.current.newsSnapshot.refresh());
  expect(result.current.selected).toBeNull();
});
it.each(['category', 'country', 'quality', 'time', 'access', 'account'] as const)(
  'invalidates supplemental selection on %s changes',
  async (change) => {
    const { result } = await selectArticle();
    act(() => {
      if (change === 'category') result.current.toggleCategory('news');
      if (change === 'country') result.current.setCountry('FR');
      if (change === 'quality') result.current.quality.setFilter('unplotted');
      if (change === 'time') result.current.setWindow(0.1);
      if (change === 'access') invalidateWorkspaceAccess();
      if (change === 'account')
        useAuthStore.setState({ user: { ...plainUser, id: 'other-account' } });
    });
    expect(result.current.selected).toBeNull();
    await waitFor(() => expect(result.current.newsSnapshot.loading).toBe(false));
    expect(result.current.selected).toBeNull();
  },
);
it('still clears selected mirror events when they leave the live collection', async () => {
  const { result } = await selectArticle();
  act(() => result.current.select(aircraft.id));
  act(() => useEventsStore.getState().applyExpire([aircraft.id]));
  expect(result.current.selected).toBeNull();
});

it('releases view-owned selection when leaving the dashboard', async () => {
  const { unmount } = await selectArticle();
  unmount();
  expect(useEventsStore.getState().selectedId).toBeNull();
  useEventsStore.getState().select('ordinary-mirror-selection');
  useEventsStore.getState().applyUpsert([liveEvent({ id: 'new-aircraft', category: 'aviation' })]);
  expect(useEventsStore.getState().selectedId).toBeNull();
});
it('keeps a selected article while either collection retains it, then clears final removal', async () => {
  const { result } = await selectArticle();
  act(() => useEventsStore.getState().applyUpsert([article]));
  articles = [];
  await act(() => result.current.newsSnapshot.refresh());
  expect(result.current.selected?.id).toBe(article.id);
  await act(() => useEventsStore.getState().load());
  expect(result.current.selected).toBeNull();
});
