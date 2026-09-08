import { act, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import type { Layer } from '@deck.gl/core';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { server } from '@/test/server';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import type { GroundStation, Cable } from '@/lib/api/infrastructure';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const station: GroundStation = {
  id: 'station',
  name: 'Test ground station',
  operator: 'ESA',
  country: 'SE',
  longitude: 20,
  latitude: 67,
  source_url: 'https://esa.int/',
  note: 'Approximate locality.',
};
const cable: Cable = {
  id: 'cable',
  name: 'Dateline cable segment',
  category: 'telecom',
  path: [
    [179, 20],
    [-179, 21],
  ],
  source_url: 'https://www.openstreetmap.org/way/1',
  note: 'Approximate incomplete route.',
};
const layers = () => (MapboxOverlay.instances[0]?.props.layers ?? []) as Layer[];
const pick = (id: string, object: unknown) => {
  const layer = layers().find((value) => value.id === id);
  if (!layer) throw new Error(`Missing ${id}`);
  const onClick = layer.props.onClick as (info: unknown) => void;
  act(() => onClick({ object }));
};
beforeEach(async () => {
  // Resolve the lazy route before asserting UI behaviour, independently of chunk compilation time.
  await import('../GlobePage');
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(
    http.get('/api/map-infrastructure', () =>
      HttpResponse.json({
        cables: [cable],
        ground_stations: [station],
        snapshot_date: '2026-09-08',
        cable_attribution: 'OpenStreetMap contributors',
        cable_licence_url: 'https://opendatacommons.org/licenses/odbl/',
      }),
    ),
  );
});
it.each(['globe', 'map'] as const)(
  'selects, highlights and closes infrastructure on the %s without keeping event selection',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Infrastructure' }));
    await user.click(screen.getByRole('switch', { name: 'Satellite ground stations' }));
    await user.click(screen.getByRole('switch', { name: 'Undersea cables' }));
    await waitFor(() =>
      expect(layers().some((layer) => layer.id === 'satellite-ground-stations')).toBe(true),
    );
    expect(layers().find((layer) => layer.id === 'undersea-cables')?.props.wrapLongitude).toBe(
      true,
    );
    pick('satellite-ground-stations', station);
    expect(screen.getByRole('complementary', { name: 'Infrastructure details' })).toHaveTextContent(
      station.name,
    );
    expect(layers().some((layer) => layer.id === 'selected-ground-station-halo')).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
    expect(layers().some((layer) => layer.id === 'selected-ground-station-halo')).toBe(false);
    pick('satellite-ground-stations', station);
    act(() =>
      useEventsStore
        .getState()
        .applyUpsert([
          liveEvent({ id: 'infra-other', category: 'news', title: 'Other infrastructure event' }),
        ]),
    );
    await user.click(screen.getByRole('button', { name: /Other infrastructure event/ }));
    expect(layers().some((layer) => layer.id === 'selected-ground-station-halo')).toBe(false);
    expect(screen.getByRole('complementary', { name: 'Event details' })).toBeInTheDocument();
    pick('undersea-cables', cable);
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Infrastructure details' })).toHaveTextContent(
      cable.name,
    );
    await user.click(screen.getByRole('switch', { name: 'Undersea cables' }));
    expect(layers().some((layer) => layer.id === 'undersea-cables')).toBe(false);
    expect(
      screen.queryByRole('complementary', { name: 'Infrastructure details' }),
    ).not.toBeInTheDocument();
  },
);
