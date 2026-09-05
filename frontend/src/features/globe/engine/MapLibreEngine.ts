/**
 * MapLibre GL JS 6 implementation of MapEngine. Uses the OpenFreeMap dark style
 * (keyless, attribution required), the `globe` projection preset (a sphere that
 * flattens to Mercator only between zoom 10 and 12) and a dark sky so the globe
 * has its atmosphere glow. Covered by a mocked smoke test only: jsdom has no WebGL.
 */
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { Layer } from '@deck.gl/core';
import { Map as MapLibreMap } from 'maplibre-gl';
import type { RequestParameters, SkySpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import type {
  CursorHandler,
  DataLayer,
  EngineOptions,
  FlyToTarget,
  MapEngine,
  MapEngineEvent,
  MapEngineHandler,
  Projection,
} from './MapEngine';
import {
  RASTER_LAYER_ID,
  RASTER_SOURCE_ID,
  hidesVectorLabels,
  isApiRequest,
  rasterSourceFor,
} from './baseLayers';
import type { BaseLayer } from './baseLayers';

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
  private baseLayer: BaseLayer = 'dark';
  private lite = false;
  private styleReady = false;

  constructor(private readonly options: EngineOptions = {}) {}

  mount(container: HTMLElement): void {
    if (this.map !== null) return;
    const map = new MapLibreMap({
      container,
      style: DARK_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      transformRequest: (url) => this.transformRequest(url),
    });
    // deck.gl draws the data layers in its own canvas above the base map.
    this.overlay = new MapboxOverlay({ interleaved: false, layers: [] });
    map.addControl(this.overlay);
    map.on('style.load', () => {
      this.styleReady = true;
      this.applySky();
      for (const [layer, property, value] of PAINT_OVERRIDES) {
        if (map.getLayer(layer) !== undefined) map.setPaintProperty(layer, property, value);
      }
      this.applyProjection();
      this.applyBaseLayer();
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

  setBaseLayer(layer: BaseLayer): void {
    this.baseLayer = layer;
    this.applyBaseLayer();
  }

  setLite(lite: boolean): void {
    this.lite = lite;
    this.applySky();
  }

  flyTo(target: FlyToTarget): void {
    if (this.lite) this.map?.jumpTo({ center: target.center, zoom: target.zoom });
    else this.map?.flyTo({ center: target.center, zoom: target.zoom });
  }

  onCursor(handler: CursorHandler): () => void {
    const map = this.map;
    if (map === null) return () => undefined;
    const listener = (event: { lngLat: { lng: number; lat: number } }) => {
      handler({ lon: event.lngLat.lng, lat: event.lngLat.lat });
    };
    map.on('mousemove', listener);
    return () => {
      map.off('mousemove', listener);
    };
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

  /** Our own tile proxy needs the session token; third-party tiles must never see it. */
  private transformRequest(url: string): RequestParameters {
    const token = this.options.authHeader?.() ?? null;
    if (token === null || !isApiRequest(url, window.location.origin)) return { url };
    return { url, headers: { Authorization: `Bearer ${token}` } };
  }

  private applySky(): void {
    if (this.map === null || !this.styleReady) return;
    this.map.setSky(this.lite ? { ...GLOBE_SKY, 'atmosphere-blend': 0 } : GLOBE_SKY);
  }

  private applyProjection(): void {
    if (this.map === null || !this.styleReady) return;
    this.map.setProjection({ type: this.projection });
  }

  private applyBaseLayer(): void {
    const map = this.map;
    if (map === null || !this.styleReady) return;
    if (map.getLayer(RASTER_LAYER_ID) !== undefined) map.removeLayer(RASTER_LAYER_ID);
    if (map.getSource(RASTER_SOURCE_ID) !== undefined) map.removeSource(RASTER_SOURCE_ID);
    const layers = map.getStyle().layers;
    const source = rasterSourceFor(this.baseLayer);
    if (source !== null) {
      map.addSource(RASTER_SOURCE_ID, source);
      // Under boundaries and labels, above the flat land and water fills.
      const above = layers.find((layer) => layer.type === 'line' || layer.type === 'symbol');
      map.addLayer({ id: RASTER_LAYER_ID, type: 'raster', source: RASTER_SOURCE_ID }, above?.id);
    }
    const visibility = hidesVectorLabels(this.baseLayer) ? 'none' : 'visible';
    for (const layer of layers) {
      if (layer.type === 'symbol') map.setLayoutProperty(layer.id, 'visibility', visibility);
    }
  }
}

export function createMapLibreEngine(options: EngineOptions = {}): MapEngine {
  return new MapLibreEngine(options);
}
