import { describe, expect, it } from 'vitest';

import { LIVE_LAYER_IDS, readLiveView, type LiveViewState } from './liveViewState';

const view: LiveViewState = {
  version: 1,
  projection: 'map',
  camera: { center: [24.5, 57.2], zoom: 4.5, bearing: 10, pitch: 0 },
  base_layer: 'dark',
  layers: ['aviation', 'aircraft', 'interference'],
  window_hours: 24,
  nation: 'EE',
  filters: { flight: 'military', gnss_level: 'red', gnss_minimum: 10 },
  plan_id: null,
};

describe('readLiveView', () => {
  it('returns a valid saved view unchanged with nothing dropped', () => {
    expect(readLiveView(view)).toEqual({ view, dropped: [] });
  });

  it('drops retired layers, unknown filters and bad filter values with names', () => {
    const result = readLiveView({
      ...view,
      layers: ['aviation', 'retired_layer', 'aviation'],
      base_layer: 'retired_base',
      filters: { flight: 'military', legacy_filter: 'x', gnss_minimum: 7, cyber_query: 'lockbit' },
    });
    expect(result.view.layers).toEqual(['aviation']);
    expect(result.view.base_layer).toBeNull();
    expect(result.view.filters).toEqual({ flight: 'military', cyber_query: 'lockbit' });
    expect(result.dropped).toEqual([
      'layer retired_layer',
      'base map retired_base',
      'filter legacy_filter',
      'filter gnss_minimum',
    ]);
  });

  it.each([
    null,
    { ...view, version: 2 },
    { ...view, projection: 'mercator' },
    { ...view, camera: { center: [500, 0], zoom: 2, bearing: 0, pitch: 0 } },
    { ...view, window_hours: -1 },
    { ...view, layers: 'aviation' },
    { ...view, plan_id: 42 },
  ])('rejects a document that is not a usable view', (payload) => {
    expect(() => readLiveView(payload)).toThrow('This saved view cannot be opened.');
  });

  it('knows every event category plus traffic and overlay switches', () => {
    expect(LIVE_LAYER_IDS).toContain('conflict');
    expect(LIVE_LAYER_IDS).toContain('aircraft');
    expect(LIVE_LAYER_IDS).toContain('terminator');
    expect(new Set(LIVE_LAYER_IDS).size).toBe(LIVE_LAYER_IDS.length);
  });
});
