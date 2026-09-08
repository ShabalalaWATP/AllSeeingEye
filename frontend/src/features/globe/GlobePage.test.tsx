import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { USER_TOKEN, liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { FOCUS_ZOOM } from './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

interface PickableLayer {
  id: string;
  props: { onClick: (info: { object?: unknown }) => boolean };
}

function overlayLayerIds(): string[] {
  const layers = MapboxOverlay.instances[0]?.props.layers as PickableLayer[] | undefined;
  return (layers ?? []).map((layer) => layer.id);
}

describe('GlobePage', () => {
  beforeEach(() => {
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
  });

  it('mounts the engine on the globe projection by default and switches to Mercator', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    expect(await screen.findByRole('region', { name: '3D globe' })).toBeInTheDocument();
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    const map = FakeMap.instances[0]!;
    expect(map.options).toMatchObject({
      style: 'https://tiles.openfreemap.org/styles/dark',
      center: [10, 30],
      zoom: 1.6,
    });
    expect(map.options.container).toBe(screen.getByTestId('map-container'));
    expect(map.setProjection).not.toHaveBeenCalled();

    act(() => {
      map.fire('style.load');
    });
    expect(map.setSky).toHaveBeenCalledWith(
      expect.objectContaining({ 'atmosphere-blend': expect.any(Array) }),
    );
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });

    const toolbar = screen.getByRole('group', { name: 'View mode' });
    expect(within(toolbar).getByRole('button', { name: 'Globe' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await user.click(within(toolbar).getByRole('button', { name: 'Map' }));
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
    expect(useGlobeStore.getState().mode).toBe('map');
    expect(screen.getByRole('region', { name: 'Map' })).toBeInTheDocument();

    await user.click(within(toolbar).getByRole('button', { name: 'Globe' }));
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });
  });

  it('loads events into the panel, the ticker and one layer per located category', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    expect(await screen.findByRole('switch', { name: 'Disasters 1' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Layers and settings' }));
    expect(screen.getByRole('switch', { name: 'Cyber 1' })).toBeInTheDocument();
    expect(screen.getByText('2 events, 0.0 of 1 MB')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    const strip = screen.getByRole('navigation', { name: 'Latest events' });
    expect(within(strip).getAllByRole('button')).toHaveLength(2);
    await waitFor(() => {
      expect(overlayLayerIds()).toEqual(['terminator', 'events-disaster']);
    });

    await user.click(screen.getByRole('switch', { name: 'Disasters 1' }));
    expect(screen.getByRole('switch', { name: 'Disasters 1' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(overlayLayerIds()).toEqual(['terminator']);
  });

  it('streams new events, opens the inspector on pick and focuses from the ticker', async () => {
    mockWebGl2(true);
    const { user, unmount } = renderApp('/', 'user');
    await screen.findByRole('switch', { name: 'Disasters 1' });
    const client = FakeEventStreamClient.instances[0]!;
    expect(client.start).toHaveBeenCalledTimes(1);
    await expect(client.options.getToken(false)).resolves.toBe(USER_TOKEN);

    const flood = liveEvent({
      id: 'e9',
      title: 'Flash flood in Valencia',
      published_at: '2026-09-05T02:00:00Z',
      point: { lon: -0.38, lat: 39.47 },
    });
    act(() => {
      client.setStatus('live');
      client.emit({
        event: 'event.upsert',
        data: JSON.stringify({ source_id: 'gdacs', events: [flood] }),
        id: null,
      });
    });
    await user.click(screen.getByRole('button', { name: 'Layers and settings' }));
    expect(screen.getByText('Live').closest('[role="status"]')).toHaveTextContent('Live');
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    expect(await screen.findByRole('switch', { name: 'Disasters 2' })).toBeInTheDocument();
    const strip = screen.getByRole('navigation', { name: 'Latest events' });
    expect(within(strip).getAllByRole('button')[0]).toHaveTextContent('Flash flood in Valencia');

    const layers = MapboxOverlay.instances[0]!.props.layers as PickableLayer[];
    const disasters = layers.find((layer) => layer.id === 'events-disaster')!;
    act(() => {
      disasters.props.onClick({ object: flood });
    });
    const drawer = screen.getByRole('complementary', { name: 'Event details' });
    expect(
      within(drawer).getByRole('heading', { name: 'Flash flood in Valencia' }),
    ).toBeInTheDocument();
    await user.click(within(drawer).getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();

    await user.click(within(strip).getByRole('button', { name: /^Flash flood in Valencia/ }));
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledWith({
      center: [-0.38, 39.47],
      zoom: FOCUS_ZOOM,
    });
    expect(screen.getByRole('complementary', { name: 'Event details' })).toBeInTheDocument();

    act(() => {
      client.emit({
        event: 'event.expire',
        data: JSON.stringify({ ids: ['e9'], count: 1 }),
        id: null,
      });
    });
    await waitFor(() =>
      expect(
        screen.queryByRole('complementary', { name: 'Event details' }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole('switch', { name: 'Disasters 1' })).toBeInTheDocument();

    unmount();
    expect(client.stop).toHaveBeenCalledTimes(1);
  });

  it('switches base layers and enables OS styles only when the server proxies them', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    const map = FakeMap.instances[0]!;
    act(() => {
      map.fire('style.load');
    });
    await user.click(screen.getByRole('button', { name: 'Map style' }));
    const group = screen.getByRole('group', { name: 'Base layer' });
    expect(within(group).getByRole('radio', { name: 'OS Road' })).toBeDisabled();
    await user.click(within(group).getByRole('radio', { name: 'Satellite' }));
    expect(useGlobeStore.getState().baseLayer).toBe('satellite');
    expect(map.addSource).toHaveBeenCalledWith(
      'ase-base-raster',
      expect.objectContaining({ type: 'raster' }),
    );
    expect(within(group).getByRole('radio', { name: 'Satellite' })).toBeChecked();
    // Our tile proxy gets the session token; nothing else does.
    const transform = map.options.transformRequest as (url: string) => {
      headers?: Record<string, string>;
    };
    expect(transform('http://localhost:3000/api/tiles/os/Road_3857/7/1/1.png').headers).toEqual({
      Authorization: `Bearer ${USER_TOKEN}`,
    });
    expect(transform('https://tiles.maps.eox.at/a.jpg').headers).toBeUndefined();
  });

  it('shows the Ordnance Survey styles when the server has a key', async () => {
    mockWebGl2(true);
    server.use(
      http.get('/api/capabilities', () =>
        HttpResponse.json({
          os_maps: true,
          os_layers: ['Light_3857', 'Outdoor_3857', 'Road_3857'],
        }),
      ),
    );
    const { user } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Map style' }));
    const osRoad = screen.getByRole('radio', { name: 'OS Road' });
    await waitFor(() => expect(osRoad).toBeEnabled());
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    act(() => {
      FakeMap.instances[0]!.fire('style.load');
    });
    await user.click(osRoad);
    expect(FakeMap.instances[0]!.addSource).toHaveBeenLastCalledWith(
      'ase-base-raster',
      expect.objectContaining({ tiles: ['/api/tiles/os/Road_3857/{z}/{x}/{y}.png'] }),
    );
  });

  it('filters the globe to one nation and flies there', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    await screen.findByRole('switch', { name: 'Disasters 1' });
    await user.click(screen.getByRole('button', { name: 'Find nation' }));
    const picker = await screen.findByRole('combobox', { name: 'Nation filter' });
    await user.type(picker, 'Ukraine');
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledWith({ center: [31.2, 48.4], zoom: 4 });
    const panel = screen.getByRole('region', { name: 'Ukraine panel' });
    expect(
      within(panel).getByText('Nothing in the live tier for this nation.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Disasters 0' })).toBeInTheDocument();
    expect(overlayLayerIds()).toEqual(['terminator']);
    const strip = screen.getByRole('navigation', { name: 'Latest events' });
    expect(within(strip).getByText('Waiting for events')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear nation filter' }));
    expect(screen.queryByRole('region', { name: 'Ukraine panel' })).not.toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Disasters 1' })).toBeInTheDocument();
    expect(overlayLayerIds()).toEqual(['terminator', 'events-disaster']);
  });

  it('drops the terminator, atmosphere and animation in lite mode and reads the cursor', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    await waitFor(() => {
      expect(overlayLayerIds()).toEqual(['terminator', 'events-disaster']);
    });
    const map = FakeMap.instances[0]!;
    act(() => {
      map.fire('style.load');
    });
    expect(map.setSky).toHaveBeenLastCalledWith(
      expect.objectContaining({ 'atmosphere-blend': expect.any(Array) }),
    );
    await user.click(screen.getByRole('switch', { name: 'Day and night on' }));
    expect(overlayLayerIds()).toEqual(['events-disaster']);
    await user.click(screen.getByRole('switch', { name: 'Day and night off' }));
    expect(overlayLayerIds()).toEqual(['terminator', 'events-disaster']);

    await user.click(screen.getByRole('button', { name: 'Layers and settings' }));
    await user.click(screen.getByRole('switch', { name: 'Lite mode off' }));
    expect(useGlobeStore.getState().lite).toBe(true);
    expect(overlayLayerIds()).toEqual(['events-disaster']);
    expect(map.setSky).toHaveBeenLastCalledWith(expect.objectContaining({ 'atmosphere-blend': 0 }));
    const strip = screen.getByRole('navigation', { name: 'Latest events' });
    await user.click(within(strip).getAllByRole('button')[0]!);
    expect(map.jumpTo).toHaveBeenCalledWith({ center: [10, 50], zoom: FOCUS_ZOOM });
    expect(map.flyTo).not.toHaveBeenCalled();

    act(() => {
      map.fire('mousemove', { lngLat: { lng: -0.1278, lat: 51.5074 } });
    });
    expect(screen.getByRole('button', { name: 'Copy coordinates' })).toHaveTextContent(
      '51.5074° N, 0.1278° W',
    );
  });

  it('asks the session for a fresh token when the stream says so', async () => {
    mockWebGl2(true);
    renderApp('/', 'user');
    await screen.findByRole('switch', { name: 'Disasters 1' });
    const client = FakeEventStreamClient.instances[0]!;
    // No CSRF cookie in this test, so the refresh fails and the session is dropped.
    await expect(client.options.getToken(true)).resolves.toBeNull();
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it('destroys the engine when the page unmounts', async () => {
    mockWebGl2(true);
    const { unmount } = renderApp('/', 'user');
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    unmount();
    expect(FakeMap.instances[0]!.remove).toHaveBeenCalledTimes(1);
  });

  it('explains that WebGL2 is required but still lists events', async () => {
    mockWebGl2(false);
    renderApp('/', 'user');
    expect(await screen.findByText('WebGL2 is required')).toBeInTheDocument();
    expect(screen.queryByTestId('map-container')).not.toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'View mode' })).toBeInTheDocument();
    expect(await screen.findByRole('switch', { name: 'Disasters 1' })).toBeInTheDocument();
    expect(FakeMap.instances).toHaveLength(0);
    expect(MapboxOverlay.instances).toHaveLength(0);
  });

  it('treats a throwing canvas probe as unsupported', async () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => {
      throw new Error('no canvas');
    });
    renderApp('/', 'user');
    expect(await screen.findByText('WebGL2 is required')).toBeInTheDocument();
  });
});
