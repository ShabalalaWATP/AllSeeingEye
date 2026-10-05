import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { MapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { useCountriesStore } from '@/stores/countries';
import { prepareCyberMap, useCyberFiltersStore } from '@/stores/cyberFilters';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { useLiveViewStore } from '@/stores/liveView';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { countries, liveEvent } from '@/test/fixtures';
import { applySession, renderApp } from '@/test/render';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const camera = { center: [24, 57] as [number, number], zoom: 5, bearing: 12, pitch: 20 };
function savedView(projection: LiveViewState['projection']): LiveViewState {
  return {
    version: 1,
    projection,
    camera,
    base_layer: 'hybrid',
    layers: ['disaster'],
    window_hours: null,
    nation: null,
    filters: {},
    plan_id: null,
  };
}

beforeEach(() => {
  applySession('user');
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ mode: 'globe', lite: false, terminator: false, opsRoom: false });
  useLiveViewStore.getState().reset();
  useCyberFiltersStore.getState().reset();
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});
afterEach(() => {
  vi.restoreAllMocks();
  useLiveViewStore.getState().reset();
  useCyberFiltersStore.getState().reset();
});

it.each(['globe', 'map'] as const)(
  'applies an already pending %s view only after engine mount and matching projection',
  async (projection) => {
    const projected = vi.spyOn(MapLibreEngine.prototype, 'setProjection');
    const restored = vi.spyOn(MapLibreEngine.prototype, 'restoreCamera');
    useLiveViewStore.getState().openView(savedView(projection));
    renderApp('/', 'user');
    await screen.findByText('Natural hazards: 1 loaded');
    const map = FakeMap.instances[0]!;
    expect(useLiveViewStore.getState().request).toBeNull();
    expect(map.jumpTo).toHaveBeenCalledExactlyOnceWith(camera);
    const matching = projected.mock.calls.findIndex(
      ([value]) => value === (projection === 'map' ? 'mercator' : 'globe'),
    );
    expect(matching).toBeGreaterThanOrEqual(0);
    expect(projected.mock.invocationCallOrder[matching]).toBeLessThan(
      restored.mock.invocationCallOrder[0]!,
    );
    expect(FakeMap.instances).toHaveLength(1);
    expect(FakeEventStreamClient.instances).toHaveLength(1);
  },
);

it('synchronises a changed projection before restoring an ops-room camera on a mounted map', async () => {
  renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  const map = FakeMap.instances[0]!;
  act(() => map.fire('style.load'));
  map.setProjection.mockClear();
  map.jumpTo.mockClear();
  act(() => useLiveViewStore.getState().openView(savedView('map')));
  expect(screen.getByRole('region', { name: 'Map' })).toBeInTheDocument();
  expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
  expect(map.jumpTo).toHaveBeenCalledExactlyOnceWith(camera);
  expect(map.setProjection.mock.invocationCallOrder.at(-1)).toBeLessThan(
    map.jumpTo.mock.invocationCallOrder[0]!,
  );
});

it('retains an authorised pending cyber focus until the engine exists with warm country data', async () => {
  useCountriesStore.setState({
    items: countries,
    byIso: Object.fromEntries(countries.map((country) => [country.iso2, country])),
    loaded: true,
    error: null,
  });
  const event = liveEvent({
    id: 'pending-cyber',
    category: 'cyber',
    subtype: 'ransomware',
    country_iso: 'GB',
    point: { lon: 7, lat: 8 },
    geo_confidence: 'exact',
    published_at: new Date().toISOString(),
  });
  prepareCyberMap({ event });
  renderApp('/', 'user');
  await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
  expect(useCyberFiltersStore.getState().pending).toBeNull();
  expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledExactlyOnceWith({ center: [7, 8], zoom: 5 });
});

it('discards a saved camera superseded by the final projection choice instead of replaying it later', async () => {
  renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  const map = FakeMap.instances[0]!;
  const unsubscribe = useGlobeStore.subscribe((next) => {
    if (next.mode === 'map') useGlobeStore.getState().setMode('globe');
  });
  try {
    // A newer choice wins before the saved view's requested projection can commit.
    act(() => useLiveViewStore.getState().openView(savedView('map')));
    expect(useGlobeStore.getState().mode).toBe('globe');
    expect(useLiveViewStore.getState().request).toBeNull();
    expect(map.jumpTo).not.toHaveBeenCalled();
  } finally {
    unsubscribe();
  }
  act(() => useGlobeStore.getState().setMode('map'));
  expect(screen.getByRole('region', { name: 'Map' })).toBeInTheDocument();
  expect(map.jumpTo).not.toHaveBeenCalled();
});
