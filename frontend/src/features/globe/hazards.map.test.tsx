import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
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
import { server } from '@/test/server';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

const records = [
  liveEvent({
    id: 'hazard-quake',
    category: 'disaster',
    subtype: 'earthquake',
    point: { lon: -120, lat: 40 },
  }),
  liveEvent({
    id: 'hazard-flood',
    category: 'disaster',
    subtype: 'flood',
    point: { lon: 60, lat: 10 },
  }),
  liveEvent({
    id: 'hazard-volcano',
    category: 'disaster',
    subtype: 'volcano',
    point: { lon: 140, lat: -20 },
  }),
  liveEvent({
    id: 'hazard-fire',
    category: 'disaster',
    subtype: 'wildfires',
    source_id: 'nasa_eonet',
    point: { lon: -60, lat: -20 },
  }),
  liveEvent({
    id: 'hazard-thermal',
    category: 'disaster',
    subtype: 'thermal_detection',
    source_id: 'firms_viirs_noaa20',
    point: { lon: 20, lat: 40 },
  }),
  liveEvent({
    id: 'hazard-plane',
    category: 'aviation',
    subtype: 'aircraft',
    point: { lon: 90, lat: 50 },
  }),
];

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(
    http.get('/api/events', () => HttpResponse.json({ items: records, count: records.length })),
    http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })),
  );
});

function eventIds() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: LiveEvent[] } }[] | undefined;
  return [
    ...new Set(
      layers?.flatMap((layer) =>
        ['event-icons', 'events-disaster', 'events-aviation', 'approximate-events'].includes(
          layer.id,
        )
          ? layer.props.data.map((event) => event.id)
          : [],
      ),
    ),
  ].sort();
}

it.each(['globe', 'map'] as const)(
  'combines earthquakes and floods on the %s without turning on Fires',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    act(() => useEventsStore.getState().toggleCategory('aviation'));
    expect(eventIds()).toEqual(['hazard-plane']);
    expect(screen.getByRole('switch', { name: /^Natural hazards / })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(screen.getByRole('switch', { name: /^Fires / })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    await user.click(screen.getByRole('button', { name: 'Natural hazard filters' }));
    const panel = screen.getByRole('region', { name: 'Natural hazard filters' });
    expect(within(panel).queryByRole('radio')).not.toBeInTheDocument();
    expect(
      within(panel).queryByRole('checkbox', { name: /wildfire|thermal|fires/i }),
    ).not.toBeInTheDocument();
    await user.click(within(panel).getByRole('button', { name: 'Clear hazard types' }));
    await user.click(within(panel).getByRole('checkbox', { name: /^Earthquakes:/ }));
    await user.click(within(panel).getByRole('checkbox', { name: /^Floods:/ }));
    expect(eventIds()).toEqual(['hazard-plane']);
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() =>
      expect(eventIds()).toEqual(['hazard-flood', 'hazard-plane', 'hazard-quake']),
    );
    expect(screen.getByRole('switch', { name: /^Fires / })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    await user.click(within(panel).getByRole('checkbox', { name: /^Earthquakes:/ }));
    await waitFor(() => expect(eventIds()).toEqual(['hazard-flood', 'hazard-plane']));
    await user.click(within(panel).getByRole('checkbox', { name: /^Floods:/ }));
    await waitFor(() => expect(eventIds()).toEqual(['hazard-plane']));
    await user.click(within(panel).getByRole('button', { name: 'Select all hazard types' }));
    await waitFor(() =>
      expect(eventIds()).toEqual([
        'hazard-flood',
        'hazard-plane',
        'hazard-quake',
        'hazard-volcano',
      ]),
    );
    expect(eventIds()).not.toContain('hazard-fire');
    expect(eventIds()).not.toContain('hazard-thermal');
  },
);
