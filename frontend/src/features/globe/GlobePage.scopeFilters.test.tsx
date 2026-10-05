import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

function newsRows() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: LiveEvent[] } }[] | undefined;
  return (layers ?? [])
    .filter((item) => ['events-news', 'approximate-events'].includes(item.id))
    .flatMap((item) => item.props.data.filter((event) => event.category === 'news'));
}

beforeEach(() => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ mode: 'globe', terminator: false, opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

it('preserves publisher and quality choices across panel navigation, nation changes and corrections', async () => {
  const exact = liveEvent({
    id: 'bbc-exact',
    category: 'news',
    source_id: 'bbc_world',
    title: 'Original located news',
    country_iso: 'GB',
    geo_confidence: 'exact',
    point: { lon: -100, lat: 10 },
  });
  const approximate = {
    ...exact,
    id: 'bbc-approximate',
    country_iso: 'UA',
    geo_confidence: 'city' as const,
    point: { lon: 80, lat: -40 },
  };
  const other = {
    ...exact,
    id: 'other-publisher',
    source_id: 'guardian_world',
    point: { lon: 0, lat: 50 },
  };
  server.use(
    http.get('/api/events', ({ request }) => {
      const country = new URL(request.url).searchParams.get('country');
      const items = [exact, approximate, other].filter(
        (event) => country === null || event.country_iso === country,
      );
      return HttpResponse.json({ items, count: items.length });
    }),
  );
  const { user, router } = renderApp('/', 'user');
  await waitFor(() => expect(newsRows()).toHaveLength(3));
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  await screen.findByRole('option', { name: 'bbc world' });
  await user.selectOptions(screen.getByRole('combobox', { name: 'Publisher' }), 'bbc_world');
  expect(
    newsRows()
      .map((event) => event.id)
      .sort(),
  ).toEqual(['bbc-approximate', 'bbc-exact']);

  await openMapTool(user, 'Location quality');
  await user.selectOptions(screen.getByLabelText('Show on map or globe'), 'reported');
  expect(newsRows().map((event) => event.id)).toEqual(['bbc-exact']);
  await openMapTool(user, 'Find nation');
  await user.type(await screen.findByRole('combobox', { name: 'Nation filter' }), 'Ukraine');
  expect(useEventsStore.getState().country).toBe('UA');
  expect(newsRows()).toEqual([]);
  await user.click(screen.getByRole('button', { name: 'Clear nation filter' }));
  await waitFor(() => expect(newsRows().map((event) => event.id)).toEqual(['bbc-exact']));

  const corrected = { ...exact, title: 'Corrected located news', geo_confidence: 'city' as const };
  act(() => useEventsStore.getState().applyUpsert([corrected]));
  expect(newsRows()).toEqual([]);
  await openMapTool(user, 'Location quality');
  expect(screen.getByLabelText('Show on map or globe')).toHaveValue('reported');
  await user.selectOptions(screen.getByLabelText('Show on map or globe'), 'all');
  expect(
    newsRows()
      .map((event) => event.id)
      .sort(),
  ).toEqual(['bbc-approximate', 'bbc-exact']);
  expect(newsRows().find((event) => event.id === exact.id)).toBe(corrected);

  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByRole('combobox', { name: 'Publisher' })).toHaveValue('bbc_world');
  expect(screen.getByRole('heading', { name: 'Corrected located news' })).toBeVisible();
  const newsAddress = router.state.location.search;
  await openMapTool(user, 'Map style');
  await act(() => router.navigate(-1));
  expect(router.state.location.search).toBe(newsAddress);
  expect(screen.getByRole('combobox', { name: 'Publisher' })).toHaveValue('bbc_world');
  expect(newsRows().find((event) => event.id === exact.id)).toBe(corrected);
  expect(FakeEventStreamClient.instances).toHaveLength(1);
  expect(FakeMap.instances).toHaveLength(1);
});
