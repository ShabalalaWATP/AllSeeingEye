import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useGlobeStore } from '@/stores/globe';
import type { NewsCountryContext } from './useNewsCountryContext';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

const indexedAt = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const located = liveEvent({
  id: 'news-city',
  title: 'News signal: Consultation in London',
  category: 'news',
  subtype: 'news_consultation',
  source_id: 'gdelt_news',
  country_iso: 'GB',
  geo_confidence: 'city',
  point: { lon: -0.1, lat: 51.5 },
  published_at: null,
  source_dates: [
    {
      field: 'DATEADDED',
      method: 'gdelt-dateadded-utc-v1',
      role: 'unspecified',
      basis: 'source_spec',
      status: 'resolved',
      precision: 'instant',
      calendar: 'gregorian',
      value: indexedAt,
      raw_text: indexedAt.replace(/\D/g, ''),
      limitations: ['Indexing time only'],
    },
  ],
});
const country = {
  ...located,
  id: 'news-country',
  title: 'Country-level public reporting',
  point: null,
  geo_confidence: 'country' as const,
};
const unlocated = {
  ...located,
  id: 'news-headline',
  title: 'A headline without supplied geography',
  point: null,
  country_iso: null,
  geo_confidence: 'none' as const,
};
interface Layer {
  id: string;
  props: {
    data: unknown[];
    onClick: (info: { object: unknown }) => boolean;
    getLineColor: (group: unknown) => number[];
  };
}
const layer = (id: string) =>
  (MapboxOverlay.instances[0]?.props.layers as Layer[] | undefined)?.find((item) => item.id === id);

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
});

it.each(['globe', 'map'] as const)(
  'loads a geographic News sample with one toggle on the %s, including country references',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const requests: string[] = [];
    server.use(
      http.get('/api/events', ({ request }) => {
        const url = new URL(request.url);
        if (
          url.searchParams.get('sampling') === 'geographic' &&
          url.searchParams.get('categories')?.includes('news')
        ) {
          expect(url.searchParams.get('time_basis')).toBe('map_record_time');
          requests.push(request.url);
          return HttpResponse.json({ items: [located, country, unlocated], count: 3 });
        }
        return HttpResponse.json({ items: [], count: 0 });
      }),
    );
    const { user } = renderApp('/', 'user');
    const toggle = await screen.findByRole('switch', { name: 'News 0' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(requests).toHaveLength(0);
    await user.click(toggle);
    await screen.findByRole('switch', { name: 'News 3' });
    await waitFor(() => expect(layer('event-icons')?.props.data).toContainEqual(located));
    expect(layer('event-icons')?.props.data).not.toContainEqual(unlocated);
    const group = layer('news-country-icons')!.props.data[0] as NewsCountryContext;
    expect(group.events).toEqual([country]);
    act(() => {
      layer('news-country-icons')!.props.onClick({ object: group });
    });
    const details = screen.getByRole('complementary', { name: 'News country context details' });
    expect(within(details).getByText(/not an exact event location/)).toBeVisible();
    expect(layer('news-country-badges')!.props.getLineColor(group)).toEqual([255, 255, 255, 255]);
    await user.click(within(details).getByRole('button', { name: 'Close news country context' }));
    expect(layer('news-country-badges')!.props.getLineColor(group)).not.toEqual([
      255, 255, 255, 255,
    ]);
    act(() => {
      layer('event-icons')!.props.onClick({ object: located });
    });
    expect(
      within(screen.getByRole('complementary', { name: 'Event details' })).getByText(located.title),
    ).toBeVisible();
    await user.click(screen.getByRole('switch', { name: 'News 3' }));
    await waitFor(() => expect(layer('news-country-icons')).toBeUndefined());
    expect(layer('event-icons')).toBeUndefined();
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('switch', { name: /^News \d/ }));
    await waitFor(() => expect(layer('news-country-icons')).toBeDefined());
    act(() => {
      layer('news-country-icons')!.props.onClick({ object: group });
    });
    await user.click(
      within(screen.getByRole('complementary', { name: 'News country context details' })).getByRole(
        'button',
        { name: country.title },
      ),
    );
    expect(
      within(screen.getByRole('complementary', { name: 'Event details' })).getByText(country.title),
    ).toBeVisible();
    await user.click(screen.getByRole('switch', { name: /^News \d/ }));
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  },
);
