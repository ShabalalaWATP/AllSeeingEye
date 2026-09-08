import { act, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { liveEvent } from '@/test/fixtures';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

function selection() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: { id: string }[] } }[] | undefined;
  return layers?.find((layer) => layer.id === 'selected-event-halo')?.props.data[0]?.id;
}

it.each(['globe', 'map'] as const)(
  'selects aircraft and vessels from searchable controls on the %s, clearing highlights on close',
  async (mode) => {
    // Complete the lazy route import before timing network/selection assertions.
    await import('./GlobePage');
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    const aircraft = liveEvent({
      id: 'find-flight',
      title: 'Military aircraft target',
      category: 'aviation',
      subtype: 'military_aircraft',
      attributes: { icao24: 'abc789' },
      point: { lon: 25, lat: 15 },
    });
    const ship = liveEvent({
      id: 'find-ship',
      title: 'Military vessel target',
      category: 'maritime',
      subtype: 'vessel_position',
      attributes: { military: true, mmsi: 987654321 },
      point: { lon: 45, lat: 10 },
    });
    act(() => {
      useEventsStore.getState().applyUpsert([aircraft, ship]);
      useEventsStore.getState().toggleCategory('aviation');
    });
    for (const [event, label, search, term] of [
      [aircraft, 'Flight filters', 'Search aircraft', 'abc789'],
      [ship, 'Boat list', 'Search vessels', '987654321'],
    ] as const) {
      const opener = screen.getByRole('button', { name: label });
      await user.click(opener);
      await user.type(screen.getByRole('searchbox', { name: search }), term);
      await user.click(
        within(
          screen.getByRole('list', {
            name:
              event.category === 'aviation' ? 'aircraft search results' : 'vessels search results',
          }),
        ).getByRole('button', { name: new RegExp(event.title) }),
      );
      await waitFor(() => expect(selection()).toBe(event.id));
      expect(FakeMap.instances[0]?.flyTo).toHaveBeenLastCalledWith({
        center: [event.point?.lon, event.point?.lat],
        zoom: 5,
      });
      expect(
        within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('heading', {
          name: event.title,
        }),
      ).toBeVisible();
      await user.click(screen.getByRole('button', { name: 'Close' }));
      await waitFor(() => expect(selection()).toBeUndefined());
      expect(useEventsStore.getState().selectedId).toBeNull();
      expect(opener).toHaveFocus();
    }
  },
);
