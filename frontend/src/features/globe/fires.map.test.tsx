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
    id: 'fire-report',
    title: 'Reported wildfire',
    category: 'disaster',
    source_id: 'nasa_eonet',
    subtype: 'wildfires',
    point: { lon: -70, lat: -20 },
  }),
  liveEvent({
    id: 'fire-thermal',
    title: 'FIRMS thermal observation',
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
  liveEvent({
    id: 'other-volcano',
    category: 'disaster',
    subtype: 'volcano',
    point: { lon: -130, lat: 50 },
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
  'controls fire sources independently from natural hazards in %s and clears a hidden selection',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    act(() => {
      useEventsStore.getState().toggleCategory('aviation');
    });
    expect(screen.getByRole('switch', { name: /^Fires / })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(screen.queryByRole('switch', { name: /^FIRMS / })).not.toBeInTheDocument();
    expect(iconIds()).toEqual(['fire-plane']);
    expect(useEventsStore.getState().hidden).toContain('disaster');
    await user.click(screen.getByRole('switch', { name: /^Fires / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report', 'fire-thermal']));
    expect(screen.getByRole('switch', { name: /^Natural hazards / })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    await user.click(screen.getByRole('button', { name: 'Fire filters' }));
    const panel = screen.getByRole('region', { name: 'Fire filters' });
    await user.click(within(panel).getByRole('checkbox', { name: /^FIRMS thermal detections:/ }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report']));
    await user.click(within(panel).getByRole('checkbox', { name: /^Reported wildfires:/ }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane']));
    await user.click(within(panel).getByRole('checkbox', { name: /^FIRMS thermal detections:/ }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-thermal']));
    await user.click(within(panel).getByRole('checkbox', { name: /^Reported wildfires:/ }));
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() =>
      expect(iconIds()).toEqual(['fire-plane', 'fire-report', 'fire-thermal', 'other-volcano']),
    );
    await user.click(screen.getByRole('switch', { name: /^Natural hazards / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane', 'fire-report', 'fire-thermal']));
    const layers = MapboxOverlay.instances[0]?.props.layers as {
      id: string;
      props: { onClick: (info: { object: LiveEvent }) => void };
    }[];
    act(() =>
      layers.find((layer) => layer.id === 'event-icons')!.props.onClick({ object: records[0]! }),
    );
    expect(screen.getByRole('complementary', { name: 'Event details' })).toBeInTheDocument();
    expect(useEventsStore.getState().selectedId).toBe('fire-report');
    await user.click(screen.getByRole('switch', { name: /^Fires / }));
    await waitFor(() => expect(iconIds()).toEqual(['fire-plane']));
    expect(useEventsStore.getState().selectedId).toBeNull();
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  },
);
