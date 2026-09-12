import { Map as MapLibreMap } from 'maplibre-gl';
import type { RequestParameters } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import type { EngineOptions } from './MapEngine';
import { isApiRequest } from './baseLayers';
import { CAMERA_MAX_PITCH, CAMERA_MAX_ZOOM } from './camera';
import { ATTRIBUTION_OPTIONS, collapseInitialAttribution } from './mapAttribution';

export const INITIAL_CENTER: [number, number] = [10, 30];
export const INITIAL_ZOOM = 1.6;

/** Construct a bounded map canvas, keeping credentials restricted to our tile proxy. */
export function createBaseMap(
  container: HTMLElement,
  style: string,
  options: EngineOptions,
): MapLibreMap {
  const map = new MapLibreMap({
    container,
    style,
    center: INITIAL_CENTER,
    zoom: INITIAL_ZOOM,
    minZoom: 0,
    maxZoom: CAMERA_MAX_ZOOM,
    minPitch: 0,
    maxPitch: CAMERA_MAX_PITCH,
    attributionControl: ATTRIBUTION_OPTIONS,
    // Two canvases at native 3x DPR would need nine times the framebuffer memory.
    pixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
    maxTileCacheSize: 128,
    ...(options.captureEnabled
      ? {
          interactive: false,
          pixelRatio: 1,
          canvasContextAttributes: { preserveDrawingBuffer: true },
        }
      : {}),
    transformRequest: (url): RequestParameters => {
      const token = options.authHeader?.() ?? null;
      if (token === null || !isApiRequest(url, window.location.origin)) return { url };
      return { url, headers: { Authorization: `Bearer ${token}` } };
    },
  });
  collapseInitialAttribution(container);
  return map;
}
