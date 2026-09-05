import { describe, expect, it } from 'vitest';

import {
  BASE_LAYER_OPTIONS,
  EOX_ATTRIBUTION,
  EOX_TILES,
  OS_ATTRIBUTION,
  OS_BOUNDS,
  hidesVectorLabels,
  isApiRequest,
  isOsLayer,
  rasterSourceFor,
} from './baseLayers';

describe('base layer specifications', () => {
  it('lists the dark style first and marks the OS styles as keyed', () => {
    expect(BASE_LAYER_OPTIONS[0]?.id).toBe('dark');
    expect(BASE_LAYER_OPTIONS.filter((option) => option.needsOs).map((o) => o.id)).toEqual([
      'os_road',
      'os_outdoor',
      'os_light',
    ]);
    expect(isOsLayer('os_light')).toBe(true);
    expect(isOsLayer('hybrid')).toBe(false);
  });

  it('describes imagery for satellite and hybrid and nothing for dark', () => {
    expect(rasterSourceFor('dark')).toBeNull();
    const satellite = rasterSourceFor('satellite');
    expect(satellite).toMatchObject({
      type: 'raster',
      tiles: [EOX_TILES],
      attribution: EOX_ATTRIBUTION,
    });
    expect(rasterSourceFor('hybrid')).toEqual(satellite);
  });

  it('points OS styles at the proxy with the Great Britain bounds and free zoom range', () => {
    const road = rasterSourceFor('os_road');
    expect(road).toMatchObject({
      tiles: ['/api/tiles/os/Road_3857/{z}/{x}/{y}.png'],
      bounds: OS_BOUNDS,
      minzoom: 7,
      maxzoom: 16,
      attribution: OS_ATTRIBUTION,
    });
    expect(rasterSourceFor('os_outdoor')).toMatchObject({
      tiles: ['/api/tiles/os/Outdoor_3857/{z}/{x}/{y}.png'],
    });
    expect(rasterSourceFor('os_light')).toMatchObject({
      tiles: ['/api/tiles/os/Light_3857/{z}/{x}/{y}.png'],
    });
  });

  it('hides the vector labels under imagery without labels and under OS tiles', () => {
    expect(hidesVectorLabels('dark')).toBe(false);
    expect(hidesVectorLabels('hybrid')).toBe(false);
    expect(hidesVectorLabels('satellite')).toBe(true);
    expect(hidesVectorLabels('os_road')).toBe(true);
  });

  it('recognises requests to our own API only', () => {
    const origin = 'http://localhost:3000';
    expect(isApiRequest('http://localhost:3000/api/tiles/os/Road_3857/7/1/1.png', origin)).toBe(
      true,
    );
    expect(isApiRequest('/api/tiles/os/Road_3857/7/1/1.png', origin)).toBe(true);
    expect(isApiRequest('http://localhost:3000/assets/x.png', origin)).toBe(false);
    expect(isApiRequest('https://evil.example/api/tiles', origin)).toBe(false);
    expect(isApiRequest('https://tiles.maps.eox.at/x.jpg', origin)).toBe(false);
    expect(isApiRequest('::not a url::', 'not an origin')).toBe(false);
  });
});
