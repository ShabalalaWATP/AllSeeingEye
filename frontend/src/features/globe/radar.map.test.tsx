import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { countries } from '@/test/fixtures';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import type { RadarAttackCountry } from './radarAttackCountries';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

interface RadarLayer {
  id: string;
  props: {
    data: RadarAttackCountry[];
    onClick: (info: { object: RadarAttackCountry }) => boolean;
    getBackgroundColor: (row: RadarAttackCountry) => number[];
  };
}
const layer = () =>
  (MapboxOverlay.instances[0]?.props.layers as RadarLayer[] | undefined)?.find(
    (item) => item.id === 'radar-attack-country-shares',
  );
const snapshot = {
  status: 'ready',
  fetched_at: '2026-09-13T12:00:00Z',
  source_url: 'https://radar.cloudflare.com/',
  layers: [
    {
      layer: 'layer3',
      period_from: '2026-09-12T00:00:00Z',
      period_to: '2026-09-13T00:00:00Z',
      updated_at: '2026-09-13T01:00:00Z',
      unit: 'bytes',
      countries: [
        { country_iso: 'GB', country_name: 'United Kingdom', rank: 1, share_percent: 12.4 },
      ],
    },
    {
      layer: 'layer7',
      period_from: '2026-09-12T00:00:00Z',
      period_to: '2026-09-13T00:00:00Z',
      updated_at: '2026-09-13T01:00:00Z',
      unit: 'requests',
      countries: [
        { country_iso: 'GB', country_name: 'United Kingdom', rank: 2, share_percent: 8.6 },
      ],
    },
  ],
};

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  useEventsStore.setState({ hidden: ['cyber'] });
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
});

it.each(['globe', 'map'] as const)(
  'loads Cloudflare target-country shares on the %s when Cyber is enabled and clears selection',
  async (mode) => {
    useGlobeStore.setState({ mode });
    let reads = 0;
    server.use(
      http.get('/api/cyber/radar-attacks', () => {
        reads += 1;
        return HttpResponse.json(snapshot);
      }),
    );
    const { user } = renderApp('/', 'user');
    const cyber = await screen.findByRole('switch', { name: 'Cyber 0' });
    expect(reads).toBe(0);
    expect(layer()).toBeUndefined();
    await user.click(cyber);
    await waitFor(() => expect(layer()?.props.data).toHaveLength(1));
    expect(reads).toBe(1);
    const row = layer()!.props.data[0]!;
    expect(row.country.iso2).toBe('GB');
    expect(row.layer3).toBe(12.4);
    expect(row.layer7).toBe(8.6);
    act(() => {
      layer()!.props.onClick({ object: row });
    });
    const inspector = screen.getByRole('complementary', {
      name: 'Cloudflare traffic country details',
    });
    expect(within(inspector).getByText(/not an attack location/)).toBeVisible();
    expect(layer()!.props.getBackgroundColor(row)).toEqual([107, 33, 168, 255]);
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledWith(
      expect.objectContaining({ center: countries.find((item) => item.iso2 === 'GB')!.centroid }),
    );
    await user.click(
      within(inspector).getByRole('button', { name: 'Close Cloudflare traffic details' }),
    );
    expect(layer()!.props.getBackgroundColor(row)).toEqual([49, 23, 79, 245]);
    await user.click(screen.getByRole('button', { name: 'Cyber filters' }));
    const panel = screen.getByRole('region', { name: 'Cyber threat intelligence filters' });
    expect(within(panel).getByText(/Purple CF labels/)).toBeVisible();
    await user.click(
      within(panel).getByRole('checkbox', { name: 'Show Cloudflare observed traffic on map' }),
    );
    expect(layer()).toBeUndefined();
    await user.click(
      within(panel).getByRole('checkbox', { name: 'Show Cloudflare observed traffic on map' }),
    );
    await waitFor(() => expect(layer()?.props.data).toHaveLength(1));
    await user.click(screen.getByRole('switch', { name: /^Cyber \d+/ }));
    expect(layer()).toBeUndefined();
  },
);
