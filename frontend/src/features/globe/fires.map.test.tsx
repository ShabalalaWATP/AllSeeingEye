import { act, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

function iconIds() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: LiveEvent[] } }[] | undefined;
  return (
    layers
      ?.find((layer) => layer.id === 'event-icons')
      ?.props.data.map((event) => event.id)
      .sort() ?? []
  );
}

it.each(['globe', 'map'] as const)(
  'combines fire evidence in %s while respecting both switches and preserving aircraft',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    act(() => {
      useEventsStore.getState().toggleCategory('aviation');
      useEventsStore.getState().applyUpsert([
        liveEvent({
          id: 'fire-report',
          category: 'disaster',
          source_id: 'nasa_eonet',
          subtype: 'wildfires',
          point: { lon: -70, lat: -20 },
        }),
        liveEvent({
          id: 'fire-thermal',
          category: 'disaster',
          source_id: 'firms_viirs_noaa20',
          subtype: 'thermal_detection',
          point: { lon: 30, lat: 10 },
        }),
        liveEvent({
          id: 'fire-plane',
          category: 'aviation',
          subtype: 'aircraft',
          point: { lon: 110, lat: 40 },
        }),
      ]);
    });
    await user.click(screen.getByRole('button', { name: 'Natural hazard filters' }));
    await user.click(screen.getByRole('radio', { name: /^Fires:/ }));
    expect(iconIds()).toEqual(['fire-plane']);
    expect(useEventsStore.getState().hidden).toContain('disaster');
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report', 'fire-thermal']));
    await user.click(screen.getByRole('switch', { name: /^FIRMS / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report']));
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane']));
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report']));
  },
);
