import { act, screen, waitFor, within } from '@testing-library/react';
import { beforeAll, beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { server } from '@/test/server';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import type { LiveEvent } from '@/lib/api/eventSchemas';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
beforeAll(async () => {
  await import('./GlobePage');
});
beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});
interface PickLayer {
  id: string;
  props: {
    data: unknown[];
    onClick: (info: { object: unknown; x?: number; y?: number }) => boolean;
  };
}
function layer(id: string) {
  return (MapboxOverlay.instances[0]?.props.layers as PickLayer[] | undefined)?.find(
    (item) => item.id === id,
  );
}
it.each(['globe', 'map'] as const)(
  'opens flight, vessel, thermal and satellite details on the %s',
  async (mode) => {
    useGlobeStore.setState({ mode });
    renderApp('/', 'user');
    await waitFor(() => expect(layer('events-disaster')).toBeDefined());
    const events = [
      { category: 'aviation', subtype: 'aircraft_position', title: 'Flight details' },
      { category: 'maritime', subtype: 'vessel_position', title: 'Vessel details' },
      { category: 'disaster', subtype: 'thermal_detection', title: 'Thermal detection details' },
      { category: 'space', subtype: 'satellite_position', title: 'Satellite details' },
    ].map((item, index) =>
      liveEvent({
        ...item,
        category: item.category as LiveEvent['category'],
        id: `pick-${index}`,
        published_at: new Date().toISOString(),
        point: { lon: index * 20, lat: 5 },
      }),
    );
    act(() => useEventsStore.getState().applyUpsert(events));
    for (const event of events) {
      await act(() =>
        layer(event.category === 'space' ? 'events-space' : 'event-icons')!.props.onClick({
          object: event,
        }),
      );
      expect(
        within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('heading', {
          name: event.title,
        }),
      ).toBeVisible();
      expect(screen.queryByRole('complementary', { name: 'Map details' })).not.toBeInTheDocument();
    }
  },
);
it('opens clustered coincident items as a selectable list before showing one event inspector', async () => {
  const { user } = renderApp('/', 'user');
  await waitFor(() => expect(layer('events-disaster')).toBeDefined());
  act(() =>
    useEventsStore.getState().applyUpsert(
      ['First record', 'Second record', 'Third record'].map((title, index) =>
        liveEvent({
          id: `cluster-${index}`,
          title,
          category: 'news',
          point: { lon: 1, lat: 1 },
          published_at: new Date().toISOString(),
        }),
      ),
    ),
  );
  const clusters = layer('clusters')!;
  await act(() => clusters.props.onClick({ object: clusters.props.data[0] }));
  const details = screen.getByRole('complementary', { name: 'Map details' });
  await user.click(within(details).getByRole('button', { name: 'Second record' }));
  expect(screen.queryByRole('complementary', { name: 'Map details' })).not.toBeInTheDocument();
  expect(
    within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('heading', {
      name: 'Second record',
    }),
  ).toBeVisible();
});
it('opens actual GNSS cell observations without claiming an emitter or a measured boundary', async () => {
  const cell = { lon: 5, lat: 50, size: 1, good: 80, bad: 20, percent_bad: 20, level: 'amber' };
  server.use(
    http.get('/api/trackers/aviation/jamming', () =>
      HttpResponse.json({ cells: [cell], updated_at: null }),
    ),
  );
  useGlobeStore.setState({ interference: true });
  const { user } = renderApp('/', 'user');
  await waitFor(() => expect(layer('gnss-interference')).toBeDefined());
  await act(() => layer('gnss-interference')!.props.onClick({ object: cell }));
  expect(screen.getByText('20 poor; 80 good')).toBeVisible();
  expect(
    screen.getByText(/not a measured interference boundary or an emitter location/),
  ).toBeVisible();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('complementary', { name: 'Map details' })).not.toBeInTheDocument();
});

it.each([true, false])(
  'offers mixed-category overlaps, exact coincidence: %s',
  async (coincident) => {
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(layer('events-disaster')).toBeDefined());
    const first = liveEvent({
      id: 'overlap-air',
      title: 'Overlapping aircraft',
      category: 'aviation',
      subtype: 'aircraft_position',
      point: { lon: 30, lat: 10 },
      published_at: new Date().toISOString(),
    });
    const second = liveEvent({
      id: 'overlap-news',
      title: 'Overlapping news',
      category: 'news',
      point: { lon: coincident ? 30 : 30.001, lat: 10 },
      published_at: new Date().toISOString(),
    });
    act(() => useEventsStore.getState().applyUpsert([first, second]));
    MapboxOverlay.instances[0]!.pickMultipleObjects.mockReturnValue([
      { object: first },
      { object: second },
    ]);
    await act(() =>
      layer('event-icons')!.props.onClick({
        object: first,
        ...(!coincident ? { x: 100, y: 100 } : {}),
      }),
    );
    const details = screen.getByRole('complementary', { name: 'Map details' });
    await user.click(within(details).getByRole('button', { name: second.title }));
    expect(
      within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('heading', {
        name: second.title,
      }),
    ).toBeVisible();
    if (!coincident)
      expect(MapboxOverlay.instances[0]!.pickMultipleObjects).toHaveBeenCalledWith({
        x: 100,
        y: 100,
        radius: 4,
        depth: 64,
      });
  },
);

it('expands a cluster obscured by a sampled aircraft using only current visible event IDs', async () => {
  const { user } = renderApp('/', 'user');
  await waitFor(() => expect(layer('events-disaster')).toBeDefined());
  const first = liveEvent({
    id: 'sampled-aircraft',
    title: 'Sampled aircraft',
    category: 'aviation',
    subtype: 'aircraft_position',
    point: { lon: 30, lat: 10 },
    published_at: new Date().toISOString(),
  });
  const second = liveEvent({
    id: 'under-cluster',
    title: 'Cluster member underneath',
    category: 'news',
    point: { lon: 30.01, lat: 10 },
    published_at: new Date().toISOString(),
  });
  act(() => useEventsStore.getState().applyUpsert([first, second]));
  MapboxOverlay.instances[0]!.pickMultipleObjects.mockReturnValue([
    { object: first },
    {
      object: { id: 'cluster-hidden', members: [second, { id: 'unknown', title: 'Stale event' }] },
    },
  ]);
  await act(() => layer('event-icons')!.props.onClick({ object: first, x: 100, y: 100 }));
  const details = screen.getByRole('complementary', { name: 'Map details' });
  expect(within(details).queryByText('Stale event')).not.toBeInTheDocument();
  await user.click(within(details).getByRole('button', { name: second.title }));
  expect(
    within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('heading', {
      name: second.title,
    }),
  ).toBeVisible();
});
