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
import type { GroundStation, Cable, DataCentre, NuclearFacility } from '@/lib/api/infrastructure';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
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
const centre: DataCentre = {
  id: 'osm-node-1',
  name: 'Docklands DC',
  operator: 'Op',
  country: 'GB',
  longitude: -0.02,
  latitude: 51.5,
  website: 'https://op.example/',
  source_url: 'https://www.openstreetmap.org/node/1',
  note: 'Mapped position only.',
};
const nuclear: NuclearFacility = {
  id: 'nuclear',
  name: 'Historical nuclear plant',
  country: 'United Kingdom',
  country_code: 'GBR',
  longitude: -2,
  latitude: 54,
  capacity_mw: 1200,
  capacity_year: 2017,
  operator: null,
  source_name: 'WRI',
  source_url: 'https://datasets.wri.org/',
  geolocation_source: 'Public inventory',
  note: 'Historical location.',
};
const layers = () => (MapboxOverlay.instances[0]?.props.layers ?? []) as Layer[];
const pick = (id: string, object: unknown) => {
  const layer = layers().find((value) => value.id === id);
  if (!layer) throw new Error(`Missing ${id}`);
  const onClick = layer.props.onClick as (info: unknown) => void;
  act(() => onClick({ object }));
};
beforeEach(async () => {
  useEventsStore.setState({ hidden: [] });
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
        nuclear_facilities: [nuclear],
        nuclear_attribution: 'WRI historical inventory',
        nuclear_licence_url: 'https://creativecommons.org/licenses/by/4.0/',
        nuclear_dataset_version: '1.3.0',
        nuclear_snapshot_date: '2026-09-09',
        data_centres: [centre],
        data_centre_attribution: 'OpenStreetMap contributors',
        data_centre_licence_url: 'https://www.openstreetmap.org/copyright',
        data_centre_snapshot_date: '2026-09-13',
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
    await user.click(screen.getByRole('switch', { name: 'Nuclear power facilities' }));
    await waitFor(() =>
      expect(layers().some((layer) => layer.id === 'nuclear-facilities')).toBe(true),
    );
    pick('nuclear-facilities', nuclear);
    expect(screen.getByRole('complementary', { name: 'Infrastructure details' })).toHaveTextContent(
      nuclear.name,
    );
    expect(layers().some((layer) => layer.id === 'selected-nuclear-facility-halo')).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
    expect(layers().some((layer) => layer.id === 'selected-nuclear-facility-halo')).toBe(false);
    await user.click(screen.getByRole('switch', { name: 'Data centres' }));
    await waitFor(() => expect(layers().some((layer) => layer.id === 'data-centres')).toBe(true));
    pick('data-centres', centre);
    expect(screen.getByRole('complementary', { name: 'Infrastructure details' })).toHaveTextContent(
      'Docklands DC',
    );
    expect(screen.getByRole('link', { name: 'Operator website' })).toHaveAttribute(
      'href',
      'https://op.example/',
    );
    expect(layers().some((layer) => layer.id === 'selected-data-centre-halo')).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
    pick('satellite-ground-stations', station);
    expect(screen.getByRole('complementary', { name: 'Infrastructure details' })).toHaveTextContent(
      station.name,
    );
    expect(layers().some((layer) => layer.id === 'selected-ground-station-halo')).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
    expect(layers().some((layer) => layer.id === 'selected-ground-station-halo')).toBe(false);
    pick('satellite-ground-stations', station);
    const other = liveEvent({
      id: 'infra-other',
      category: 'news',
      title: 'Other infrastructure event',
      point: { lon: 12.345, lat: 56.789 },
    });
    act(() => useEventsStore.getState().applyUpsert([other]));
    pick('events-news', other);
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
