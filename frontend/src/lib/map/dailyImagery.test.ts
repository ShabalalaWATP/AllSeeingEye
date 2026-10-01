import { describe, expect, it } from 'vitest';

import { FakeMap } from '@/test/fakeMap';

import { RASTER_LAYER_ID, RASTER_SOURCE_ID } from './baseLayers';
import {
  DAILY_IMAGERY_LAYER_ID,
  DAILY_IMAGERY_PRODUCTS,
  DAILY_IMAGERY_SOURCE_ID,
  GIBS_ORIGIN,
  applyDailyImagery,
  dailyImageryDateRange,
  dailyImagerySource,
  dailyImageryTiles,
  defaultDailyImageryDate,
  isDailyImageryError,
  validDailyImagery,
} from './dailyImagery';
import type { Map as MapLibreMap } from 'maplibre-gl';

const now = Date.UTC(2026, 9, 1, 9, 30);

describe('daily imagery product allowlist and dates', () => {
  it('offers only fixed GIBS corrected-reflectance layers', () => {
    expect(GIBS_ORIGIN).toBe('https://gibs.earthdata.nasa.gov');
    expect(DAILY_IMAGERY_PRODUCTS.map((product) => product.layer)).toEqual([
      'MODIS_Terra_CorrectedReflectance_TrueColor',
      'MODIS_Aqua_CorrectedReflectance_TrueColor',
      'VIIRS_SNPP_CorrectedReflectance_TrueColor',
    ]);
  });

  it('defaults to yesterday in UTC and bounds the range by product and today', () => {
    expect(defaultDailyImageryDate(now)).toBe('2026-09-30');
    expect(dailyImageryDateRange('modis_terra', now)).toEqual({
      min: '2000-02-24',
      max: '2026-10-01',
    });
    expect(dailyImageryDateRange('viirs_snpp', now).min).toBe('2015-11-24');
  });

  it('accepts only real ISO calendar dates inside the product range', () => {
    expect(validDailyImagery('modis_terra', '2026-09-30', now)).toEqual({
      product: 'modis_terra',
      date: '2026-09-30',
    });
    for (const date of [
      '2026-10-02',
      '1999-12-31',
      '2026-02-30',
      '2026-9-30',
      '20260930',
      '2026-09-30T00:00:00Z',
      '2026-09-30/../../x',
      '2026-09-30?x=1',
      '',
    ]) {
      expect(validDailyImagery('modis_terra', date, now), date).toBeNull();
    }
    expect(validDailyImagery('viirs_snpp', '2015-11-23', now)).toBeNull();
    expect(validDailyImagery('unknown' as never, '2026-09-30', now)).toBeNull();
  });
});

describe('daily imagery tiles', () => {
  it('builds the fixed HTTPS WMTS template from the validated date only', () => {
    expect(dailyImageryTiles({ product: 'modis_terra', date: '2026-09-30' }, now)).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2026-09-30/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
    );
    expect(dailyImageryTiles({ product: 'modis_terra', date: '2026-13-01' }, now)).toBeNull();
  });

  it('describes a raster source that stops at the published zoom and credits NASA', () => {
    const source = dailyImagerySource({ product: 'viirs_snpp', date: '2026-09-29' }, now);
    expect(source).toMatchObject({ type: 'raster', tileSize: 256, maxzoom: 9 });
    expect(source?.tiles).toEqual([
      expect.stringMatching(/^https:\/\/gibs\.earthdata\.nasa\.gov\//),
    ]);
    expect(source?.attribution).toContain('NASA');
    expect(dailyImagerySource({ product: 'viirs_snpp', date: 'x' }, now)).toBeNull();
  });
});

describe('applyDailyImagery', () => {
  function styledMap() {
    const map = new FakeMap({});
    map.addSource(RASTER_SOURCE_ID, { type: 'raster' });
    const firstLine = map.layers.find((layer) => layer.type === 'line' || layer.type === 'symbol');
    map.addLayer({ id: RASTER_LAYER_ID, type: 'raster' }, firstLine?.id);
    return map;
  }

  it('draws above the base raster and beneath borders and labels, then removes cleanly', () => {
    const map = styledMap();
    const target = map as unknown as MapLibreMap;
    applyDailyImagery(target, { product: 'modis_aqua', date: '2026-09-30' }, now);
    const ids = map.layers.map((layer) => layer.id);
    const imagery = ids.indexOf(DAILY_IMAGERY_LAYER_ID);
    expect(imagery).toBeGreaterThan(ids.indexOf(RASTER_LAYER_ID));
    const firstLine = map.layers.findIndex(
      (layer) => layer.type === 'line' || layer.type === 'symbol',
    );
    expect(imagery).toBeLessThan(firstLine);
    expect(map.sources.get(DAILY_IMAGERY_SOURCE_ID)).toMatchObject({ maxzoom: 9 });

    applyDailyImagery(target, { product: 'modis_aqua', date: '2026-09-29' }, now);
    expect(map.layers.filter((layer) => layer.id === DAILY_IMAGERY_LAYER_ID)).toHaveLength(1);
    applyDailyImagery(target, null, now);
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
    expect(map.sources.has(DAILY_IMAGERY_SOURCE_ID)).toBe(false);
  });

  it('draws nothing for an invalid date even if one reaches the engine', () => {
    const map = styledMap();
    applyDailyImagery(map as unknown as MapLibreMap, { product: 'modis_terra', date: '../x' }, now);
    expect(map.getLayer(DAILY_IMAGERY_LAYER_ID)).toBeUndefined();
  });

  it('recognises tile failures from its own source only', () => {
    expect(isDailyImageryError({ sourceId: DAILY_IMAGERY_SOURCE_ID })).toBe(true);
    expect(isDailyImageryError({ sourceId: RASTER_SOURCE_ID })).toBe(false);
    expect(isDailyImageryError(null)).toBe(false);
    expect(isDailyImageryError('error')).toBe(false);
  });
});
