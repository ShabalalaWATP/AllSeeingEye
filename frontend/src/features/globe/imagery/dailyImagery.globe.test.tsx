import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DAILY_IMAGERY_LAYER_ID, DAILY_IMAGERY_SOURCE_ID } from '@/lib/map/dailyImagery';
import { useEventsStore } from '@/stores/events';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { useDailyImageryStore } from './dailyImageryStore';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);

describe('daily imagery on the live map', () => {
  beforeEach(() => {
    useEventsStore.setState({ hidden: [] });
    useDailyImageryStore.getState().reset();
    server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    mockWebGl2(true);
  });

  it('adds dated GIBS tiles only when switched on and degrades on tile failure', async () => {
    const { user } = renderApp('/', 'user');
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    const map = FakeMap.instances[0]!;
    act(() => {
      map.fire('style.load');
    });
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();

    await openMapTool(user, 'Map style');
    await user.click(screen.getByRole('switch', { name: 'Daily satellite imagery' }));
    expect(map.sources.get(DAILY_IMAGERY_SOURCE_ID)).toMatchObject({
      tiles: [
        `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${yesterday}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`,
      ],
    });
    const caption = screen.getByText(/MODIS Terra true colour \(morning pass\) for/);
    expect(within(caption.parentElement!).getByRole('link', { name: 'NASA GIBS' })).toHaveAttribute(
      'href',
      'https://www.earthdata.nasa.gov/gibs',
    );

    const added = map.addSource.mock.calls.length;
    act(() => {
      map.fire('error', { sourceId: 'ase-base-raster' });
    });
    expect(screen.queryByText(/Some imagery tiles did not load/)).not.toBeInTheDocument();
    act(() => {
      map.fire('error', { sourceId: DAILY_IMAGERY_SOURCE_ID });
      map.fire('error', { sourceId: DAILY_IMAGERY_SOURCE_ID });
    });
    expect(screen.getByText(/Some imagery tiles did not load/)).toBeVisible();
    // A failure neither reloads the layer nor removes the base map.
    expect(map.addSource.mock.calls.length).toBe(added);
    expect(map.getLayer('ase-base-raster')).toBeDefined();

    await user.click(screen.getByRole('switch', { name: 'Daily satellite imagery' }));
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
    expect(screen.queryByText(/MODIS Terra true colour \(morning pass\) for/)).toBeNull();
  });
});
