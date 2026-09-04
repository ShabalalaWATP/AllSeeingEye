import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FakeMap } from '@/test/fakeMap';

import { createMapLibreEngine, DARK_STYLE_URL, INITIAL_CENTER, INITIAL_ZOOM } from './MapLibreEngine';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));

describe('MapLibreEngine (mocked maplibre-gl smoke test)', () => {
  beforeEach(() => {
    FakeMap.reset();
  });

  it('mounts once, applies the projection after the style loads, flies and subscribes', () => {
    const engine = createMapLibreEngine();
    const container = document.createElement('div');
    engine.setProjection('mercator');
    engine.flyTo({ center: [0, 0], zoom: 2 });
    // Subscribing before mount is a no-op whose unsubscribe is safe to call.
    const unsubscribe = engine.on('click', () => undefined);
    unsubscribe();

    engine.mount(container);
    engine.mount(container);
    expect(FakeMap.instances).toHaveLength(1);
    const map = FakeMap.instances[0]!;
    expect(map.options).toEqual({
      container,
      style: DARK_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    expect(map.setProjection).not.toHaveBeenCalled();

    map.fire('style.load');
    expect(map.setSky).toHaveBeenCalledTimes(1);
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
});
