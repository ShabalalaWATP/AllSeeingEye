import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapBounds, MapCamera } from '@/lib/map/MapEngine';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';

import { createMapLibreEngine } from './MapLibreEngine';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

const camera: MapCamera = { center: [179, 52], zoom: 5, bearing: 35, pitch: 40 };
const bounds: MapBounds = { west: 170, east: -170, south: -10, north: 10 };

function mounted() {
  const engine = createMapLibreEngine();
  engine.mount(document.createElement('div'));
  return { engine, map: FakeMap.instances[0]! };
}

describe('shared map camera and viewport contract', () => {
  beforeEach(() => {
    FakeMap.reset();
    MapboxOverlay.reset();
  });

  it('does not invent a camera or viewport while unmounted', () => {
    const engine = createMapLibreEngine();
    expect(engine.getCamera()).toBeNull();
    expect(engine.getViewportBounds()).toBeNull();
    engine.restoreCamera(camera);
    engine.fitBounds(bounds);
    expect(FakeMap.instances).toHaveLength(0);
    engine.mount(document.createElement('div'));
    expect(FakeMap.instances[0]!.jumpTo).not.toHaveBeenCalled();
    engine.destroy();
    expect(engine.getCamera()).toBeNull();
    expect(engine.getViewportBounds()).toBeNull();
  });

  it('captures an independent normalised snapshot without changing the camera', () => {
    const { engine, map } = mounted();
    const center = { lng: 541, lat: 89 };
    vi.spyOn(map, 'getCenter').mockReturnValue(center);
    map.getBearing.mockReturnValue(395);
    map.getPitch.mockReturnValue(40);
    expect(engine.getCamera()).toEqual({ center: [-179, 89], zoom: 1.5, bearing: 35, pitch: 40 });
    const snapshot = engine.getCamera()!;
    snapshot.center[0] = 0;
    expect(center.lng).toBe(541);
    expect(map.jumpTo).not.toHaveBeenCalled();
  });

  it('accepts the explicitly configured renderer limits when capturing and restoring', () => {
    const { engine, map } = mounted();
    expect(map.options).toMatchObject({ minZoom: 0, maxZoom: 22, minPitch: 0, maxPitch: 60 });
    vi.spyOn(map, 'getZoom').mockReturnValue(22);
    map.getPitch.mockReturnValue(60);
    const snapshot = engine.getCamera()!;
    expect(snapshot).toMatchObject({ zoom: 22, pitch: 60 });
    engine.restoreCamera(snapshot);
    expect(map.jumpTo).toHaveBeenCalledWith(snapshot);
    engine.fitBounds(bounds, { padding: 4096 });
    expect(map.fitBounds).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ padding: 4096 }),
    );
  });

  it('restores immediately, stops spin and preserves the engine through projection changes', () => {
    const { engine, map } = mounted();
    map.fire('style.load');
    engine.spin(true);
    engine.restoreCamera(camera);
    expect(map.jumpTo).toHaveBeenCalledWith(camera);
    expect(map.jumpTo.mock.calls[0]![0]).not.toBe(camera);
    expect(map.stop).toHaveBeenCalledTimes(1);
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    engine.setProjection('mercator');
    engine.setProjection('globe');
    expect(FakeMap.instances).toHaveLength(1);
    expect(map.jumpTo).toHaveBeenCalledTimes(1);
    expect(map.flyTo).not.toHaveBeenCalled();
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });
  });

  it('returns wrapped viewport bounds and preserves full-world envelopes', () => {
    const { engine, map } = mounted();
    map.getBounds.mockReturnValue({
      getWest: () => 170,
      getEast: () => 190,
      getSouth: () => -10,
      getNorth: () => 10,
    });
    expect(engine.getViewportBounds()).toEqual(bounds);
    map.getBounds.mockReturnValue({
      getWest: () => -540,
      getEast: () => 190,
      getSouth: () => -90,
      getNorth: () => 90,
    });
    expect(engine.getViewportBounds()).toEqual({ west: -180, east: 180, south: -90, north: 90 });
  });

  it('fits a wrapped box using the short contiguous span without changing input geometry', () => {
    const { engine, map } = mounted();
    engine.spin(true);
    engine.fitBounds(bounds, { padding: 40, maxZoom: 10 });
    expect(map.fitBounds).toHaveBeenCalledWith(
      [
        [170, -10],
        [190, 10],
      ],
      {
        padding: 40,
        maxZoom: 10,
        duration: 0,
      },
    );
    expect(bounds.east).toBe(-170);
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    engine.fitBounds({ west: -180, east: 180, south: -90, north: 90 });
    expect(map.fitBounds).toHaveBeenLastCalledWith(
      [
        [-180, -90],
        [180, 90],
      ],
      {
        padding: 24,
        maxZoom: 16,
        duration: 0,
      },
    );
  });

  it.each([
    { ...camera, center: [Infinity, 0] },
    { ...camera, center: [0, 91] },
    { ...camera, zoom: NaN },
    { ...camera, zoom: 23 },
    { ...camera, bearing: Infinity },
    { ...camera, pitch: -1 },
    { ...camera, pitch: 61 },
  ])('rejects invalid camera values before touching the renderer: %j', (invalid) => {
    const { engine, map } = mounted();
    expect(() => engine.restoreCamera(invalid as MapCamera)).toThrow(RangeError);
    expect(map.jumpTo).not.toHaveBeenCalled();
    expect(map.stop).not.toHaveBeenCalled();
  });

  it.each([
    { ...bounds, west: NaN },
    { ...bounds, east: 181 },
    { ...bounds, south: -91 },
    { ...bounds, north: -11 },
  ])('rejects invalid bounds before fitting: %j', (invalid) => {
    const { engine, map } = mounted();
    expect(() => engine.fitBounds(invalid)).toThrow(RangeError);
    expect(map.fitBounds).not.toHaveBeenCalled();
  });

  it('rejects invalid fit options and exposes moveend for settled snapshots', () => {
    const { engine, map } = mounted();
    expect(() => engine.fitBounds(bounds, { padding: -1 })).toThrow(RangeError);
    expect(() => engine.fitBounds(bounds, { padding: 4097 })).toThrow(RangeError);
    expect(() => engine.fitBounds(bounds, { maxZoom: Infinity })).toThrow(RangeError);
    expect(map.fitBounds).not.toHaveBeenCalled();
    const changed = vi.fn();
    const off = engine.on('moveend', changed);
    map.fire('moveend');
    expect(changed).toHaveBeenCalledTimes(1);
    off();
    map.fire('moveend');
    expect(changed).toHaveBeenCalledTimes(1);
  });
});
