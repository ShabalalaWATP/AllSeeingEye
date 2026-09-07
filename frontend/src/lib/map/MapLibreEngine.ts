/**
 * MapLibre GL JS 6 implementation of MapEngine. Defaults to the OpenFreeMap dark style
 * (keyless, attribution required), the `globe` projection preset (a sphere that
 * flattens to Mercator only between zoom 10 and 12) and a dark sky so the globe
 * has its atmosphere glow. Unit tests mock the map; rendering needs browser verification.
 */
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { Layer } from '@deck.gl/core';
import { Map as MapLibreMap } from 'maplibre-gl';
import type { RequestParameters } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import type {
  CursorHandler,
  DataLayer,
  EngineOptions,
  FlyToTarget,
  FitBoundsOptions,
  MapBounds,
  MapCamera,
  MapEngine,
  MapEngineEvent,
  MapEngineHandler,
  Projection,
} from './MapEngine';
import { DARK_STYLE_URL, isApiRequest, vectorStyleFor } from './baseLayers';
import type { BaseLayer } from './baseLayers';
import {
  CAMERA_MAX_PITCH,
  CAMERA_MAX_ZOOM,
  normaliseCamera,
  normaliseViewport,
  validateBounds,
  validateFitOptions,
} from './camera';

import { GLOBE_SKY, PAINT_OVERRIDES, applyRasterLayer } from './mapAppearance';
import { captureMapImage } from './mapCapture';

export { GLOBE_SKY, PAINT_OVERRIDES } from './mapAppearance';
export { DARK_STYLE_URL };
export const INITIAL_CENTER: [number, number] = [10, 30];
export const INITIAL_ZOOM = 1.6;
export const SPIN_DEGREES = 15;
export const SPIN_STEP_MS = 30_000;

export class MapLibreEngine implements MapEngine {
  private map: MapLibreMap | null = null;
  private overlay: MapboxOverlay | null = null;
  private projection: Projection = 'globe';
  private baseLayer: BaseLayer = 'dark';
  private styleUrl = DARK_STYLE_URL;
  private lite = false;
  private styleReady = false;
  private spinning = false;
  private stepping = false;
  private revision = 0;
  private captureAbort: AbortController | null = null;
  private captureFailed = false;
  private layers: readonly Layer[] = [];

  constructor(private readonly options: EngineOptions = {}) {}

  mount(container: HTMLElement): void {
    if (this.map !== null) return;
    this.styleUrl = vectorStyleFor(this.baseLayer);
    const map = new MapLibreMap({
      container,
      style: this.styleUrl,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      minZoom: 0,
      maxZoom: CAMERA_MAX_ZOOM,
      minPitch: 0,
      maxPitch: CAMERA_MAX_PITCH,
      ...(this.options.captureEnabled
        ? {
            interactive: false,
            pixelRatio: 1,
            canvasContextAttributes: { preserveDrawingBuffer: true },
          }
        : {}),
      transformRequest: (url) => this.transformRequest(url),
    });
    // deck.gl draws the data layers in its own canvas above the base map.
    this.overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
      ...(this.options.captureEnabled
        ? {
            useDevicePixels: 1,
            onError: () => {
              this.captureFailed = true;
            },
          }
        : {}),
    });
    if (this.options.captureEnabled) {
      map.on('error', () => {
        this.captureFailed = true;
      });
      map.on('move', () => {
        this.revision += 1;
      });
      map.on('resize', () => {
        this.revision += 1;
      });
    }
    map.addControl(this.overlay);
    map.on('style.load', () => {
      this.styleReady = true;
      this.applySky();
      if (this.styleUrl === DARK_STYLE_URL) {
        for (const [layer, property, value] of PAINT_OVERRIDES) {
          if (map.getLayer(layer) !== undefined) map.setPaintProperty(layer, property, value);
        }
      }
      this.applyProjection();
      this.applyBaseLayer();
    });
    if (import.meta.env.DEV) {
      // Development aid only: lets the browser console inspect the live map.
      (window as unknown as { __aseMap?: MapLibreMap }).__aseMap = map;
    }
    map.on('moveend', () => {
      if (this.spinning) this.spinStep();
    });
    this.map = map;
  }

  spin(enabled: boolean): void {
    if (this.spinning === enabled) return;
    this.spinning = enabled;
    if (enabled) this.spinStep();
    else this.map?.stop();
  }

  /** One slow eastward step; moveend chains the next while spinning stays on. */
  private spinStep(): void {
    const map = this.map;
    if (map === null || !this.spinning) return;
    // Reduced motion can make easeTo finish synchronously and emit moveend immediately.
    if (this.stepping) {
      this.spinning = false;
      return;
    }
    const center = map.getCenter();
    this.stepping = true;
    try {
      map.easeTo({
        center: [center.lng + SPIN_DEGREES, center.lat],
        duration: SPIN_STEP_MS,
        easing: (t: number) => t,
      });
    } finally {
      this.stepping = false;
    }
  }

  setProjection(projection: Projection): void {
    this.revision += 1;
    this.projection = projection;
    this.applyProjection();
  }

  setBaseLayer(layer: BaseLayer): void {
    this.revision += 1;
    this.baseLayer = layer;
    const nextStyle = vectorStyleFor(layer);
    if (this.map !== null && this.styleUrl !== nextStyle) {
      this.styleUrl = nextStyle;
      this.styleReady = false;
      // The style.load handler restores projection, atmosphere and the latest raster choice.
      // The non-interleaved deck overlay remains mounted above the replacement style.
      this.map.setStyle(nextStyle, { diff: false });
      return;
    }
    this.applyBaseLayer();
  }

  setLite(lite: boolean): void {
    this.revision += 1;
    this.lite = lite;
    this.applySky();
  }

  flyTo(target: FlyToTarget): void {
    this.revision += 1;
    if (this.lite) this.map?.jumpTo({ center: target.center, zoom: target.zoom });
    else this.map?.flyTo({ center: target.center, zoom: target.zoom });
  }

  getZoom(): number {
    return this.map?.getZoom() ?? 0;
  }

  getCamera(): MapCamera | null {
    const map = this.map;
    if (map === null) return null;
    const center = map.getCenter();
    return normaliseCamera({
      center: [center.lng, center.lat],
      zoom: map.getZoom(),
      bearing: map.getBearing(),
      pitch: map.getPitch(),
    });
  }

  restoreCamera(camera: MapCamera): void {
    this.revision += 1;
    const snapshot = normaliseCamera(camera);
    this.spin(false);
    this.map?.jumpTo(snapshot);
  }

  getViewportBounds(): MapBounds | null {
    const bounds = this.map?.getBounds();
    if (bounds === undefined) return null;
    return normaliseViewport({
      west: bounds.getWest(),
      south: bounds.getSouth(),
      east: bounds.getEast(),
      north: bounds.getNorth(),
    });
  }

  fitBounds(bounds: MapBounds, options: FitBoundsOptions = {}): void {
    this.revision += 1;
    const { west, south, east, north } = validateBounds(bounds);
    const fitOptions = validateFitOptions(options);
    this.spin(false);
    // Use the contiguous world copy so wrapped boxes do not fit almost the whole planet.
    this.map?.fitBounds(
      [
        [west, south],
        [east < west ? east + 360 : east, north],
      ],
      {
        ...fitOptions,
        duration: 0,
      },
    );
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
    this.revision += 1;
    this.layers = layers as readonly Layer[];
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

  async captureImage(signal: AbortSignal): Promise<Blob> {
    const map = this.map;
    const overlay = this.overlay;
    if (!this.options.captureEnabled || !map || !overlay || this.captureFailed) {
      throw new Error('Map image capture is unavailable. Use a fresh export map.');
    }
    if (this.captureAbort) throw new Error('A map image capture is already running.');
    const controller = new AbortController();
    this.captureAbort = controller;
    const abort = () => controller.abort();
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) abort();
    const revision = this.revision;
    try {
      return await captureMapImage(
        map,
        overlay,
        controller.signal,
        () => this.revision === revision && !this.captureFailed,
        () => this.layers.every((layer) => layer.isLoaded),
      );
    } finally {
      signal.removeEventListener('abort', abort);
      this.captureAbort = null;
    }
  }

  destroy(): void {
    this.captureAbort?.abort();
    this.revision += 1;
    this.spinning = false;
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
    applyRasterLayer(map, this.baseLayer);
  }
}

export function createMapLibreEngine(options: EngineOptions = {}): MapEngine {
  return new MapLibreEngine(options);
}
