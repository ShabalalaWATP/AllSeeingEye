import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DAILY_IMAGERY_LAYER_ID } from '@/lib/map/dailyImagery';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';

import { createMapLibreEngine } from './MapLibreEngine';
import { RASTER_LAYER_ID } from './baseLayers';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);

function layerIds(map: FakeMap): string[] {
  return map.layers.map((layer) => layer.id);
}

describe('MapLibreEngine daily imagery', () => {
  beforeEach(() => {
    FakeMap.reset();
    MapboxOverlay.reset();
  });

  it('keeps dated imagery above the base raster across base and style changes', () => {
    const engine = createMapLibreEngine();
    engine.setBaseLayer('satellite');
    // Before mount the choice is remembered and drawn once the style has loaded.
    engine.setDailyImagery?.({ product: 'modis_terra', date: yesterday });
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
    map.fire('style.load');
    expect(layerIds(map)).toEqual([
      'background',
      'water',
      RASTER_LAYER_ID,
      DAILY_IMAGERY_LAYER_ID,
      'boundary_country_z0-4',
      'place_city',
    ]);

    engine.setBaseLayer('hybrid');
    expect(layerIds(map).indexOf(DAILY_IMAGERY_LAYER_ID)).toBe(
      layerIds(map).indexOf(RASTER_LAYER_ID) + 1,
    );

    engine.setBaseLayer('streets');
    map.fire('style.load');
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeDefined();

    engine.setDailyImagery?.(null);
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
  });

  it('draws nothing for a date outside the published range', () => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    const map = FakeMap.instances[0]!;
    map.fire('style.load');
    engine.setDailyImagery?.({ product: 'viirs_snpp', date: '2015-01-01' });
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
  });
});
