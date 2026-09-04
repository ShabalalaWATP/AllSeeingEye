/**
 * MapLibre GL JS 6 implementation of MapEngine. Uses the OpenFreeMap dark style
 * (keyless, attribution required), the `globe` projection preset (a sphere that
 * flattens to Mercator only between zoom 10 and 12) and a dark sky so the globe
 * has its atmosphere glow. Covered by a mocked smoke test only: jsdom has no WebGL.
 */
import { Map as MapLibreMap } from 'maplibre-gl';
import type { SkySpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import type {
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
  'fog-ground-blend': 0.6,
  'horizon-fog-blend': 0.7,
  'sky-horizon-blend': 0.6,
  'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0],
};

export class MapLibreEngine implements MapEngine {
  private map: MapLibreMap | null = null;
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
    map.on('style.load', () => {
      this.styleReady = true;
      map.setSky(GLOBE_SKY);
      this.applyProjection();
    });
    this.map = map;
  }

  setProjection(projection: Projection): void {
    this.projection = projection;
    this.applyProjection();
  }

  flyTo(target: FlyToTarget): void {
    this.map?.flyTo({ center: target.center, zoom: target.zoom });
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
