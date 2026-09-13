import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { countries, liveEvent } from '@/test/fixtures';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useGlobeStore } from '@/stores/globe';
import { networkCountryGroups, type NetworkCountryGroup } from './networkContext';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

const attributed = liveEvent({
  id: 'ioda-gb',
  title: 'Reported routing signal drop',
  category: 'cyber',
  subtype: 'outage',
  source_id: 'ioda_outages',
  country_iso: 'GB',
  geo_confidence: 'country',
  point: null,
  published_at: new Date().toISOString(),
});
const unlocated = liveEvent({
  ...attributed,
  id: 'ioda-unlocated',
  title: 'Unlocated network signal',
  country_iso: null,
  geo_confidence: 'none',
});
const unrelated = liveEvent({ ...attributed, id: 'another-feed', source_id: 'other' });

interface MapLayer {
  id: string;
  props: {
    data: NetworkCountryGroup[];
    onClick: (info: { object: NetworkCountryGroup }) => boolean;
    getLineColor: (group: NetworkCountryGroup) => number[];
  };
}
const layer = (id: string) =>
  (MapboxOverlay.instances[0]?.props.layers as MapLayer[] | undefined)?.find(
    (item) => item.id === id,
  );

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
  server.use(
    http.get('/api/map-infrastructure', () =>
      HttpResponse.json({
        cables: [],
        ground_stations: [],
        nuclear_facilities: [],
        nuclear_attribution: 'Test data',
        nuclear_licence_url: 'https://example.org/licence',
        nuclear_dataset_version: 'test',
        nuclear_snapshot_date: '2026-09-13',
        snapshot_date: '2026-09-13',
        cable_attribution: 'Test data',
        cable_licence_url: 'https://example.org/licence',
      }),
    ),
  );
});

it('maps only country-attributed IODA and Cloudflare network records', () => {
  const countryByIso = Object.fromEntries(countries.map((country) => [country.iso2, country]));
  const radar = liveEvent({ ...attributed, id: 'radar-gb', source_id: 'cloudflare_radar_outages' });
  const window = liveEvent({ ...attributed, id: 'ioda-window', source_id: 'ioda_outage_events' });
  expect(
    networkCountryGroups([attributed, radar, window, unlocated, unrelated], countryByIso),
  ).toEqual([{ country: countryByIso.GB, events: [attributed, radar, window] }]);
});

it.each(['globe', 'map'] as const)(
  'shows Network markers on the %s with Technology and clears a disabled selection',
  async (mode) => {
    useGlobeStore.setState({ mode });
    server.use(
      http.get('/api/events', ({ request }) =>
        HttpResponse.json({
          items:
            new URL(request.url).searchParams.get('sources') === 'ioda_outages'
              ? [attributed, unlocated]
              : [],
          count: 2,
        }),
      ),
    );
    const { user } = renderApp('/', 'user');
    expect(layer('network-country-icons')).toBeUndefined();
    await user.click(await screen.findByRole('button', { name: 'Technology & communications' }));
    expect(screen.getByRole('switch', { name: 'Connectivity signals' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    await user.click(screen.getByText('Browse connectivity signals'));
    const panel = screen.getAllByRole('region', { name: 'Connectivity signals' })[0]!;
    await waitFor(() => expect(layer('network-country-icons')?.props.data).toHaveLength(1));
    expect(within(panel).getByText(/1 source-attributed country shown on the map/)).toBeVisible();
    const group = layer('network-country-icons')!.props.data[0]!;
    expect(group.country.iso2).toBe('GB');
    expect(group.events).toEqual([attributed]);
    act(() => {
      layer('network-country-icons')!.props.onClick({ object: group });
    });
    const inspector = screen.getByRole('complementary', { name: 'Network country details' });
    expect(within(inspector).getByText(/does not locate an outage/)).toBeVisible();
    expect(layer('network-country-badges')!.props.getLineColor(group)).toEqual([
      255, 255, 255, 255,
    ]);
    await user.click(
      within(inspector).getByRole('button', { name: 'Close network country details' }),
    );
    expect(screen.queryByRole('complementary', { name: 'Network country details' })).toBeNull();
    expect(layer('network-country-badges')!.props.getLineColor(group)).toEqual([251, 191, 36, 230]);
    await user.click(within(panel).getAllByRole('button', { name: 'View details' })[0]!);
    const eventDetails = await screen.findByRole('complementary', { name: 'Event details' });
    expect(within(eventDetails).getByText('Reported routing signal drop')).toBeVisible();
    expect(layer('network-country-badges')!.props.getLineColor(group)).toEqual([
      255, 255, 255, 255,
    ]);
    await user.click(within(eventDetails).getByRole('button', { name: /close/i }));
    expect(layer('network-country-badges')!.props.getLineColor(group)).toEqual([251, 191, 36, 230]);
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    expect(layer('network-country-icons')).toBeDefined();
    await user.click(screen.getByRole('button', { name: 'Technology & communications' }));
    await user.click(screen.getByRole('switch', { name: 'Connectivity signals' }));
    expect(layer('network-country-icons')).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    await user.click(screen.getByRole('button', { name: 'Technology & communications' }));
    expect(screen.getByRole('switch', { name: 'Connectivity signals' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledWith(
      expect.objectContaining({
        center: countries.find((country) => country.iso2 === 'GB')!.centroid,
      }),
    );
  },
);
