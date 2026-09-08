import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';

import {
  createMapLibreEngine,
  DARK_STYLE_URL,
  INITIAL_CENTER,
  INITIAL_ZOOM,
} from './MapLibreEngine';
import { EOX_TILES, OS_BOUNDS, RASTER_LAYER_ID, RASTER_SOURCE_ID } from './baseLayers';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));

describe('MapLibreEngine (mocked maplibre-gl smoke test)', () => {
  beforeEach(() => {
    FakeMap.reset();
    MapboxOverlay.reset();
  });

  it('bounds both framebuffer resolutions and the tile cache on high-DPI monitors', () => {
    const ratio = vi.spyOn(window, 'devicePixelRatio', 'get').mockReturnValue(3);
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    expect(FakeMap.instances[0]!.options).toMatchObject({ pixelRatio: 1.5, maxTileCacheSize: 128 });
    expect(MapboxOverlay.instances[0]!.props.useDevicePixels).toBe(1.5);
    engine.destroy();
    ratio.mockRestore();
  });

  it('mounts once, applies the projection after the style loads, flies and subscribes', () => {
    const engine = createMapLibreEngine();
    const container = document.createElement('div');
    engine.setProjection('mercator');
    engine.flyTo({ center: [0, 0], zoom: 2 });
    engine.setLayers([{ id: 'early' }]);
    expect(MapboxOverlay.instances).toHaveLength(0);
    // Subscribing before mount is a no-op whose unsubscribe is safe to call.
    const unsubscribe = engine.on('click', () => undefined);
    unsubscribe();

    engine.mount(container);
    engine.mount(container);
    expect(FakeMap.instances).toHaveLength(1);
    const map = FakeMap.instances[0]!;
    expect(map.options).toMatchObject({
      container,
      style: DARK_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    expect(map.options.transformRequest).toBeTypeOf('function');
    expect(map.setProjection).not.toHaveBeenCalled();
    // The deck.gl overlay is attached as a control and receives the data layers.
    const overlay = MapboxOverlay.instances[0]!;
    expect(overlay.props).toMatchObject({ interleaved: false, layers: [], useDevicePixels: 1 });
    expect(map.addControl).toHaveBeenCalledWith(overlay);
    const layer = { id: 'events-disaster' };
    engine.setLayers([layer]);
    expect(overlay.setProps).toHaveBeenCalledWith({ layers: [layer] });

    map.fire('style.load');
    expect(map.setSky).toHaveBeenCalledTimes(1);
    // Palette overrides apply only to the four layers the fake style actually has.
    expect(map.setPaintProperty).toHaveBeenCalledTimes(4);
    expect(map.setPaintProperty).toHaveBeenCalledWith('water', 'fill-color', '#0b1626');
    expect(map.setPaintProperty).not.toHaveBeenCalledWith(
      'boundary_state',
      expect.anything(),
      expect.anything(),
    );
    expect(map.setProjection).toHaveBeenCalledWith({ type: 'mercator' });

    engine.setProjection('globe');
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });

    engine.flyTo({ center: [-1.5, 52.4], zoom: 6 });
    expect(map.flyTo).toHaveBeenCalledWith({ center: [-1.5, 52.4], zoom: 6 });

    const handler = vi.fn();
    const off = engine.on('move', handler);
    map.fire('move', { reason: 'test' });
    expect(handler).toHaveBeenCalledWith({ reason: 'test' });
    off();
    expect(map.off).toHaveBeenCalledWith('move', handler);

    engine.destroy();
    expect(map.remove).toHaveBeenCalledTimes(1);
    engine.destroy();
    expect(map.remove).toHaveBeenCalledTimes(1);
  });

  it('swaps raster base layers under the boundaries and hides labels where they clash', () => {
    const engine = createMapLibreEngine();
    engine.setBaseLayer('satellite'); // before mount: remembered, applied after the style loads
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    expect(map.addSource).not.toHaveBeenCalled();

    map.fire('style.load');
    expect(map.addSource).toHaveBeenCalledWith(
      RASTER_SOURCE_ID,
      expect.objectContaining({ type: 'raster', tiles: [EOX_TILES] }),
    );
    expect(map.addLayer).toHaveBeenCalledWith(
      { id: RASTER_LAYER_ID, type: 'raster', source: RASTER_SOURCE_ID },
      'boundary_country_z0-4',
    );
    expect(map.layers.map((layer) => layer.id)).toEqual([
      'background',
      'water',
      RASTER_LAYER_ID,
      'boundary_country_z0-4',
      'place_city',
    ]);
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'none');

    engine.setBaseLayer('hybrid');
    expect(map.removeLayer).toHaveBeenCalledWith(RASTER_LAYER_ID);
    expect(map.removeSource).toHaveBeenCalledWith(RASTER_SOURCE_ID);
    expect(map.addSource).toHaveBeenCalledTimes(2);
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'visible');

    engine.setBaseLayer('os_road');
    expect(map.addSource).toHaveBeenLastCalledWith(
      RASTER_SOURCE_ID,
      expect.objectContaining({
        tiles: ['/api/tiles/os/Road_3857/{z}/{x}/{y}.png'],
        bounds: OS_BOUNDS,
      }),
    );
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'none');

    engine.setBaseLayer('dark');
    expect(map.addSource).toHaveBeenCalledTimes(3);
    expect(map.layers.map((layer) => layer.id)).not.toContain(RASTER_LAYER_ID);
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'visible');
  });

  it('attaches the session token only to requests for our own API', () => {
    let token: string | null = 'session-token';
    const engine = createMapLibreEngine({ authHeader: () => token });
    engine.mount(document.createElement('div'));
    const transform = FakeMap.instances[0]!.options.transformRequest as (url: string) => {
      url: string;
      headers?: Record<string, string>;
    };
    const own = 'http://localhost:3000/api/tiles/os/Road_3857/7/1/1.png';
    expect(transform(own)).toEqual({
      url: own,
      headers: { Authorization: 'Bearer session-token' },
    });
    expect(transform('https://tiles.maps.eox.at/x.jpg')).toEqual({
      url: 'https://tiles.maps.eox.at/x.jpg',
    });
    token = null;
    expect(transform(own)).toEqual({ url: own });

    const anonymous = createMapLibreEngine();
    anonymous.mount(document.createElement('div'));
    const plain = FakeMap.instances[1]!.options.transformRequest as (url: string) => {
      url: string;
    };
    expect(plain(own)).toEqual({ url: own });
  });

  it('reloads vector styles without losing projection, overlay or pending selections', () => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    const overlay = MapboxOverlay.instances[0]!;
    map.fire('style.load');
    engine.setProjection('mercator');
    engine.setLayers([{ id: 'events' }]);
    map.setPaintProperty.mockClear();
    map.setLayoutProperty.mockClear();
    engine.setBaseLayer('streets');
    expect(map.setStyle).toHaveBeenLastCalledWith('https://tiles.openfreemap.org/styles/liberty', {
      diff: false,
    });
    // Updates while loading must not touch layers that are not ready yet.
    engine.setBaseLayer('streets');
    expect(map.setStyle).toHaveBeenCalledTimes(1);
    expect(map.setLayoutProperty).not.toHaveBeenCalled();
    map.fire('style.load');
    expect(map.setPaintProperty).not.toHaveBeenCalled();
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'visible');
    expect(map.addControl).toHaveBeenCalledTimes(1);
    expect(map.addControl).toHaveBeenCalledWith(overlay);
    expect(overlay.setProps).toHaveBeenLastCalledWith({ layers: [{ id: 'events' }] });

    engine.setBaseLayer('light');
    expect(map.setStyle).toHaveBeenLastCalledWith('https://tiles.openfreemap.org/styles/positron', {
      diff: false,
    });
    engine.setBaseLayer('satellite');
    engine.setBaseLayer('hybrid');
    expect(map.setStyle).toHaveBeenLastCalledWith(DARK_STYLE_URL, { diff: false });
    expect(map.addSource).not.toHaveBeenCalled();
    map.fire('style.load');
    expect(map.addSource).toHaveBeenCalledWith(
      RASTER_SOURCE_ID,
      expect.objectContaining({ tiles: [EOX_TILES] }),
    );
    expect(map.setPaintProperty).toHaveBeenCalled();
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'visible');
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
  });

  it('loads a remembered light style directly and hides vector linework on pure imagery', () => {
    const engine = createMapLibreEngine();
    engine.setBaseLayer('light');
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    expect(map.options.style).toBe('https://tiles.openfreemap.org/styles/positron');
    map.fire('style.load');
    expect(map.setPaintProperty).not.toHaveBeenCalled();
    engine.setBaseLayer('satellite');
    map.fire('style.load');
    expect(map.setLayoutProperty).toHaveBeenCalledWith(
      'boundary_country_z0-4',
      'visibility',
      'none',
    );
    engine.setBaseLayer('hybrid');
    expect(map.setLayoutProperty).toHaveBeenCalledWith(
      'boundary_country_z0-4',
      'visibility',
      'visible',
    );
    engine.setBaseLayer('os_road');
    expect(map.setLayoutProperty).toHaveBeenLastCalledWith('place_city', 'visibility', 'none');
  });

  it('turns the globe in slow eastward steps while spinning and stops on demand', () => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    engine.spin(true);
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    expect(map.easeTo.mock.calls[0]?.[0]).toMatchObject({ center: [25, 30], duration: 30_000 });
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(2);
    engine.spin(false);
    expect(map.stop).toHaveBeenCalledTimes(1);
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(2);
  });

  it('stops chaining when an animation completes synchronously', () => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    // MapLibre completes immediately when reduced motion changes during a spin.
    map.easeTo.mockImplementation(() => map.fire('moveend'));
    expect(() => engine.spin(true)).not.toThrow();
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(1);
  });

  it('does not restart spinning when removal finishes the current movement', () => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    engine.spin(true);
    map.remove.mockImplementation(() => map.fire('moveend'));
    engine.destroy();
    expect(map.easeTo).toHaveBeenCalledTimes(1);
  });
});
