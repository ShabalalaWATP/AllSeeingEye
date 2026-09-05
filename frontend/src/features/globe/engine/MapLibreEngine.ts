/**
 * MapLibre GL JS 6 implementation of MapEngine. Uses the OpenFreeMap dark style
 * (keyless, attribution required), the `globe` projection preset (a sphere that
 * flattens to Mercator only between zoom 10 and 12) and a dark sky so the globe
 * has its atmosphere glow. Covered by a mocked smoke test only: jsdom has no WebGL.
 */
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { Layer } from '@deck.gl/core';
import { Map as MapLibreMap } from 'maplibre-gl';
import type { SkySpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import type {
  DataLayer,
  FlyToTarget,
  MapEngine,
  MapEngineEvent,
  MapEngineHandler,
  Projection,
} from './MapEngine';

export const DARK_STYLE_URL = 'https://tiles.openfreemap.org/styles/dark';
export const INITIAL_CENTER: [number, number] = [10, 30];
export const INITIAL_ZOOM = 1.6;

/** Dark atmosphere: the glow fades out as the user zooms towards street scale. */
export const GLOBE_SKY: SkySpecification = {
  'sky-color': '#0b1230',
  'horizon-color': '#28407a',
  'fog-color': '#07070b',
  // Keep ground fog low: at planet scale the whole surface counts as "far away",
  // and a strong blend towards the dark fog colour blacks out the continents.
  'fog-ground-blend': 0.1,
  'horizon-fog-blend': 0.5,
  'sky-horizon-blend': 0.6,
  'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0],
};

/**
 * The OpenFreeMap dark style paints land at 5 percent grey and water at 11 percent,
 * which is invisible on a globe. These overrides move it onto the app palette:
 * obsidian land, deep navy water, slate borders and muted labels.
 */
type PaintOverride = readonly [
  layer: string,
  property: 'background-color' | 'fill-color' | 'line-color' | 'text-color',
  value: string,
];

export const PAINT_OVERRIDES: readonly PaintOverride[] = [
  ['background', 'background-color', '#15151d'],
  ['water', 'fill-color', '#0b1626'],
  ['waterway', 'line-color', '#0b1626'],
  ['boundary_country_z0-4', 'line-color', '#4a4a5c'],
  ['boundary_country_z5-', 'line-color', '#4a4a5c'],
  ['boundary_state', 'line-color', '#33333f'],
  ['place_country_major', 'text-color', '#9a95a3'],
  ['place_country_minor', 'text-color', '#9a95a3'],
  ['place_country_other', 'text-color', '#9a95a3'],
  ['place_city_large', 'text-color', '#7d7886'],
  ['place_city', 'text-color', '#7d7886'],
];

export class MapLibreEngine implements MapEngine {
  private map: MapLibreMap | null = null;
  private overlay: MapboxOverlay | null = null;
  private projection: Projection = 'globe';
  private styleReady = false;

  mount(container: HTMLElement): void {
    if (this.map !== null) return;
    const map = new MapLibreMap({
      container,
      style: DARK_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    // deck.gl draws the data layers in its own canvas above the base map.
    this.overlay = new MapboxOverlay({ interleaved: false, layers: [] });
    map.addControl(this.overlay);
    map.on('style.load', () => {
      this.styleReady = true;
      map.setSky(GLOBE_SKY);
      for (const [layer, property, value] of PAINT_OVERRIDES) {
        if (map.getLayer(layer) !== undefined) map.setPaintProperty(layer, property, value);
      }
      this.applyProjection();
    });
    if (import.meta.env.DEV) {
      // Development aid only: lets the browser console inspect the live map.
      (window as unknown as { __aseMap?: MapLibreMap }).__aseMap = map;
    }
    this.map = map;
  }

  setProjection(projection: Projection): void {
    this.projection = projection;
    this.applyProjection();
  }

  flyTo(target: FlyToTarget): void {
    this.map?.flyTo({ center: target.center, zoom: target.zoom });
  }

  setLayers(layers: readonly DataLayer[]): void {
    this.overlay?.setProps({ layers: [...(layers as readonly Layer[])] });
  }

  on(event: MapEngineEvent, handler: MapEngineHandler): () => void {
    const map = this.map;
    if (map === null) return () => undefined;
    map.on(event, handler);
    return () => {
      map.off(event, handler);
    };
  }

  destroy(): void {
    this.map?.remove();
    this.map = null;
    this.overlay = null;
    this.styleReady = false;
  }

  private applyProjection(): void {
    if (this.map === null || !this.styleReady) return;
    this.map.setProjection({ type: this.projection });
  }
}

export function createMapLibreEngine(): MapEngine {
  return new MapLibreEngine();
}
