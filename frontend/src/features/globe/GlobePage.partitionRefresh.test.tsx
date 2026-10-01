import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import type { LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { sameLayerRows } from '@/lib/map/sameLayerRows';
import { useEventsStore } from '@/stores/events';
import { SNAPSHOT_REFRESH_MS } from '@/stores/events.refresh';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
// Load the real route before rendering it, so the lazy import is not on the clock.
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const quake = liveEvent({ id: 'quake', point: { lon: 20, lat: 40 } });
const vessel = (title: string) =>
  liveEvent({
    id: 'vessel',
    title,
    category: 'maritime',
    // A port call draws in the maritime scatter layer; positions share the icon layer.
    subtype: 'port_call',
    source_id: 'aisstream',
    point: { lon: 4, lat: 52 },
  });
const stats: StoreStats = {
  total: 2,
  estimated_bytes: 1,
  budget_bytes: 10,
  per_category: [
    { category: 'disaster', count: 1, oldest: null, newest: null },
    { category: 'maritime', count: 1, oldest: null, newest: null },
  ],
};

interface DataLayer {
  id: string;
  props: { data: LiveEvent[] };
}

function layer(id: string): DataLayer | undefined {
  return (MapboxOverlay.instances[0]?.props.layers as DataLayer[] | undefined)?.find(
    (item) => item.id === id,
  );
}

beforeEach(() => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ terminator: false, opsRoom: false, mode: 'globe' });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});
afterEach(() => {
  vi.useRealTimers();
});

it('refreshes only the maritime partition and leaves other event layers untouched', async () => {
  let records = [quake, vessel('Before')];
  const requested: (string | null)[] = [];
  server.use(
    http.get('/api/events', ({ request }) => {
      const categories = new URL(request.url).searchParams.get('categories');
      requested.push(categories);
      const items = records.filter(
        (event) => categories === null || categories.split(',').includes(event.category),
      );
      return HttpResponse.json({ items, count: items.length });
    }),
    http.get('/api/events/stats', () => HttpResponse.json(stats)),
  );
  renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => expect(layer('events-maritime')).toBeDefined());
  const disaster = layer('events-disaster')!;
  const maritime = layer('events-maritime')!;
  requested.length = 0;
  // Only the refresh timer below is simulated; the page mounted on real time.
  vi.useFakeTimers({ shouldAdvanceTime: true });

  records = [quake, vessel('After')];
  act(() =>
    FakeEventStreamClient.instances[0]!.emit({
      event: 'event.resync',
      data: JSON.stringify({ reason: 'snapshot_required', categories: ['maritime'] }),
      id: null,
    }),
  );
  await act(() => vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS));
  await waitFor(() => expect(useEventsStore.getState().byId.vessel?.title).toBe('After'));

  // One maritime snapshot read; no unscoped or unrelated partition was requested.
  expect(requested).toEqual(['maritime']);
  expect(sameLayerRows(layer('events-disaster')!.props.data, disaster.props.data)).toBe(true);
  expect(sameLayerRows(layer('events-maritime')!.props.data, maritime.props.data)).toBe(false);
  expect(screen.getByText('Natural hazards: 1 loaded')).toBeInTheDocument();
});
