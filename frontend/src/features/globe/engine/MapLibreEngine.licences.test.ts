import { beforeEach, expect, it, vi } from 'vitest';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { createMapLibreEngine } from './MapLibreEngine';
import { RASTER_SOURCE_ID } from './baseLayers';
import { DAILY_IMAGERY_SOURCE_ID } from '@/lib/map/dailyImagery';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
});

it('never schedules denied default or restored raster and daily imagery requests', () => {
  const engine = createMapLibreEngine({ sourceAllowed: (id) => id === 'map:openfreemap' });
  engine.mount(document.createElement('div'));
  const map = FakeMap.instances[0]!;
  map.fire('style.load');
  expect(map.getSource(RASTER_SOURCE_ID)).toBeUndefined();
  engine.setBaseLayer('satellite');
  engine.setDailyImagery?.({ product: 'modis_terra', date: '2026-09-01' });
  map.fire('style.load');
  expect(map.getSource(RASTER_SOURCE_ID)).toBeUndefined();
  expect(map.getSource(DAILY_IMAGERY_SOURCE_ID)).toBeUndefined();
  engine.destroy();
});

it('does not construct a provider map while its vector dependency is denied', () => {
  const engine = createMapLibreEngine({ sourceAllowed: () => false });
  expect(() => engine.mount(document.createElement('div'))).toThrow('licence terms');
  expect(FakeMap.instances).toHaveLength(0);
});
