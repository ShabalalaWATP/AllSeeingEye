/**
 * Base layers the engine can draw under the data: the dark vector style, EOX satellite
 * imagery (alone or with labels for hybrid), and Ordnance Survey raster tiles proxied by
 * the API for Great Britain. The specifications live here so the engine stays small.
 */
import type { RasterSourceSpecification } from 'maplibre-gl';

import type { BaseLayer } from '@/stores/globe';

export type { BaseLayer };

export interface BaseLayerOption {
  id: BaseLayer;
  label: string;
  /** Needs the OS Maps proxy, which exists only when an OS key is configured. */
  needsOs: boolean;
}

export const BASE_LAYER_OPTIONS: readonly BaseLayerOption[] = [
  { id: 'dark', label: 'Dark', needsOs: false },
  { id: 'satellite', label: 'Satellite', needsOs: false },
  { id: 'hybrid', label: 'Hybrid', needsOs: false },
  { id: 'os_road', label: 'OS Road', needsOs: true },
  { id: 'os_outdoor', label: 'OS Outdoor', needsOs: true },
  { id: 'os_light', label: 'OS Light', needsOs: true },
];

export const RASTER_SOURCE_ID = 'ase-base-raster';
export const RASTER_LAYER_ID = 'ase-base-raster';

export const EOX_TILES =
  'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg';
export const EOX_ATTRIBUTION =
  'Sentinel-2 cloudless by EOX IT Services GmbH (CC BY-NC-SA 4.0), contains modified Copernicus Sentinel data 2024';
export const OS_ATTRIBUTION = 'Contains OS data © Crown copyright and database rights 2026';
/** Great Britain, the extent of the OS Maps API. */
export const OS_BOUNDS: [number, number, number, number] = [-10.76, 49.86, 1.78, 60.86];
export const OS_MIN_ZOOM = 7;
export const OS_MAX_ZOOM = 16;

const OS_LAYER_NAMES: Partial<Record<BaseLayer, string>> = {
  os_road: 'Road_3857',
  os_outdoor: 'Outdoor_3857',
  os_light: 'Light_3857',
};

export function isOsLayer(layer: BaseLayer): boolean {
  return layer in OS_LAYER_NAMES;
}

/** The raster source under the vector style for this base layer, or null for the dark style alone. */
export function rasterSourceFor(layer: BaseLayer): RasterSourceSpecification | null {
  if (layer === 'satellite' || layer === 'hybrid') {
    return {
      type: 'raster',
      tiles: [EOX_TILES],
      tileSize: 256,
      maxzoom: 18,
      attribution: EOX_ATTRIBUTION,
    };
  }
  const name = OS_LAYER_NAMES[layer];
  if (name === undefined) return null;
  return {
    type: 'raster',
    tiles: [`/api/tiles/os/${name}/{z}/{x}/{y}.png`],
    tileSize: 256,
    minzoom: OS_MIN_ZOOM,
    maxzoom: OS_MAX_ZOOM,
    bounds: OS_BOUNDS,
    attribution: OS_ATTRIBUTION,
  };
}

/** Satellite alone and the OS styles (which carry their own labels) hide the vector labels. */
export function hidesVectorLabels(layer: BaseLayer): boolean {
  return layer === 'satellite' || isOsLayer(layer);
}

/** Whether a tile request goes to our own API and so needs the session's bearer token. */
export function isApiRequest(url: string, origin: string): boolean {
  try {
    const parsed = new URL(url, origin);
    return parsed.origin === origin && parsed.pathname.startsWith('/api/');
  } catch {
    return false;
  }
}
