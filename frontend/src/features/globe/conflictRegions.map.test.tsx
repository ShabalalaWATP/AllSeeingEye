import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { conflictCard } from '@/test/fixtures.trackers';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { ORDERED_CATEGORIES } from '@/lib/categories';
import type { ConflictRegion } from './conflictRegions';
import type { LiveEvent } from '@/lib/api/eventSchemas';

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

interface TestLayer {
  id: string;
  props: { data: unknown[]; onClick: (info: { object: unknown }) => boolean; pickable: boolean };
}
function layers() {
  return MapboxOverlay.instances[0]?.props.layers as TestLayer[] | undefined;
}
function layer(id: string) {
  return layers()?.find((item) => item.id === id);
}

it('starts with only conflicts visible, without GNSS, cameras, infrastructure or day/night overlays', async () => {
  const { user } = renderApp('/', 'user');
  await waitFor(() => expect(layer('conflict-region-markers')?.props.data).toHaveLength(1));
  expect(useEventsStore.getState().hidden).toEqual(
    ORDERED_CATEGORIES.filter((category) => category !== 'conflict'),
  );
  expect(useGlobeStore.getState()).toMatchObject({ terminator: false, interference: false });
  for (const toggle of screen.getAllByRole('switch')) {
    expect(toggle).toHaveAttribute(
      'aria-checked',
      toggle.getAttribute('aria-label')?.startsWith('Conflict') ? 'true' : 'false',
    );
  }
  expect(layers()!.every((item) => item.id.startsWith('conflict-region-'))).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Event time' }));
  const time = screen.getByRole('region', { name: 'Event time' });
  expect(within(time).queryByRole('switch')).not.toBeInTheDocument();
  expect(within(time).getByRole('radio', { name: 'All' })).toBeChecked();
  expect(layers()!.every((item) => item.id.startsWith('conflict-region-'))).toBe(true);
});

it.each(['globe', 'map'] as const)(
  'selects regional markers on the %s, locates from the list and clears highlighting on close or event selection',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const reviewedReport = {
      ...conflictCard.latest!,
      attributes: { conflict_screening: 'llm', conflict_relevance: 'armed_conflict' },
    };
    server.use(
      http.get('/api/events', () => HttpResponse.json({ items: [reviewedReport], count: 1 })),
    );
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(layer('conflict-region-markers')?.props.data).toHaveLength(1));
    const region = layer('conflict-region-markers')!.props.data[0] as ConflictRegion;
    act(() => {
      layer('conflict-region-markers')!.props.onClick({ object: region });
    });
    const inspector = screen.getByRole('complementary', { name: 'Conflict region details' });
    expect(within(inspector).getByText('War region (curated)')).toBeInTheDocument();
    expect(within(inspector).getByText(/not a frontline/)).toBeInTheDocument();
    expect(within(inspector).getByText('Shelling in Kharkiv')).toBeInTheDocument();
    expect(within(inspector).getByRole('link', { name: /Open evidence/ })).toHaveAttribute(
      'href',
      '/trackers/conflicts/ukraine',
    );
    expect(layer('conflict-region-selection')!.props.data).toHaveLength(1);
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenLastCalledWith(
      expect.objectContaining({ center: [31.5, 48.25] }),
    );
    await user.click(
      within(inspector).getByRole('button', { name: 'Close conflict region details' }),
    );
    expect(layer('conflict-region-selection')!.props.data).toEqual([]);
    await user.click(screen.getByRole('button', { name: 'Conflict report filters' }));
    await user.click(screen.getByRole('button', { name: /Russia's war in Ukraine/ }));
    expect(layer('conflict-region-selection')!.props.data).toHaveLength(1);
    await user.keyboard('{Escape}');
    // First Escape closes the controls; dismiss the inspector explicitly if still open.
    const dismiss = screen.queryByRole('button', { name: 'Close conflict region details' });
    if (dismiss) await user.click(dismiss);
    expect(layer('conflict-region-selection')!.props.data).toEqual([]);
    act(() => {
      layer('conflict-region-markers')!.props.onClick({ object: region });
    });
    await waitFor(() => expect(layer('event-icons')).toBeDefined());
    act(() => {
      layer('event-icons')!.props.onClick({ object: reviewedReport });
    });
    expect(screen.getByRole('complementary', { name: 'Event details' })).toBeInTheDocument();
    expect(layer('conflict-region-selection')!.props.data).toEqual([]);
    expect(layer('event-icons')!.props.data).toEqual([reviewedReport]);
  },
);

it('provides region search, classification, hide and retry controls independently of report filters', async () => {
  const fetch = vi.fn();
  server.use(
    http.get('/api/trackers/conflicts', () => {
      fetch();
      return HttpResponse.json({ error: { code: 'offline', message: 'offline' } }, { status: 503 });
    }),
  );
  const { user } = renderApp('/', 'user');
  await user.click(await screen.findByRole('button', { name: 'Conflict report filters' }));
  await screen.findByRole('alert');
  expect(screen.getByText(/Region overview unavailable/)).toBeInTheDocument();
  server.use(
    http.get('/api/trackers/conflicts', () => {
      fetch();
      return HttpResponse.json({ items: [conflictCard] });
    }),
  );
  await user.click(screen.getByRole('button', { name: 'Refresh region overview' }));
  await screen.findByRole('button', { name: /Russia's war in Ukraine/ });
  await user.type(screen.getByRole('searchbox', { name: 'Find a conflict region' }), 'missing');
  expect(screen.getByText(/No regions match/)).toBeInTheDocument();
  await user.clear(screen.getByRole('searchbox', { name: 'Find a conflict region' }));
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Region classification' }),
    'tension',
  );
  expect(screen.getByText(/No regions match/)).toBeInTheDocument();
  await user.selectOptions(screen.getByRole('combobox', { name: 'Region classification' }), 'war');
  await user.click(screen.getByRole('checkbox', { name: 'Show regional overview markers' }));
  expect(layer('conflict-region-markers')).toBeUndefined();
  await user.click(screen.getByRole('checkbox', { name: 'Show regional overview markers' }));
  expect(layer('conflict-region-markers')).toBeDefined();
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('changes region and event symbol projection at actual zoom 12 without using clustering zoom', async () => {
  const report = {
    ...conflictCard.latest!,
    attributes: { conflict_screening: 'llm', conflict_relevance: 'armed_conflict' },
  };
  server.use(http.get('/api/events', () => HttpResponse.json({ items: [report], count: 1 })));
  renderApp('/', 'user');
  await waitFor(() => expect(layer('event-icons')).toBeDefined());
  await waitFor(() => expect(layer('conflict-region-markers')?.props.data).toHaveLength(1));
  act(() => {
    layer('conflict-region-markers')!.props.onClick({
      object: layer('conflict-region-markers')!.props.data[0],
    });
  });
  const map = FakeMap.instances[0]!;
  const zoom = vi.spyOn(map, 'getZoom');
  const move = (value: number) => {
    zoom.mockReturnValue(value);
    act(() => map.fire('move'));
  };
  const expectGlobe = (globe: boolean) => {
    for (const id of ['conflict-region-markers', 'conflict-region-labels', 'event-icons']) {
      expect(layer(id)!.props).toMatchObject({ parameters: { 2886: 2304 } });
      const props = layer(id)!.props as unknown as {
        billboard: boolean;
        getAngle: number | ((event: LiveEvent) => number);
      };
      expect(props.billboard).toBe(!globe);
      expect(typeof props.getAngle === 'function' ? props.getAngle(report) : props.getAngle).toBe(
        globe ? 180 : 0,
      );
    }
  };
  move(12);
  expectGlobe(true);
  move(12.01);
  expectGlobe(false);
  move(11.9);
  expectGlobe(true);
  act(() => useGlobeStore.getState().setMode('map'));
  expectGlobe(false);
  act(() => useGlobeStore.getState().setMode('globe'));
  expectGlobe(true);
});
