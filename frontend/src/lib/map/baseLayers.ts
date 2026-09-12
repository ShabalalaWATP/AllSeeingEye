/**
 * Base layers under the data: three OpenFreeMap vector styles, EOX satellite imagery
 * (alone or with labels for hybrid), and Ordnance Survey rasters proxied by the API for
 * Great Britain. Keeping provider specifications here leaves the engine independent of URLs.
 */
import type { RasterSourceSpecification } from 'maplibre-gl';

/** What is drawn under data in either globe or flat-map projection. */
export type BaseLayer =
  'dark' | 'streets' | 'light' | 'satellite' | 'hybrid' | 'os_road' | 'os_outdoor' | 'os_light';

export const DEFAULT_BASE_LAYER: BaseLayer = 'hybrid';

export interface BaseLayerOption {
  id: BaseLayer;
  label: string;
  description: string;
  coverage: string;
  /** Needs the OS Maps proxy, which exists only when an OS key is configured. */
  needsOs: boolean;
}

export const BASE_LAYER_OPTIONS = [
  {
    id: 'dark',
    label: 'Dark',
    needsOs: false,
    description: 'Quiet cartography for monitoring event overlays.',
    coverage: 'Worldwide · OpenFreeMap',
  },
  {
    id: 'streets',
    label: 'Streets',
    needsOs: false,
    description: 'Roads, places and points of interest using the Liberty style.',
    coverage: 'Worldwide · OpenFreeMap',
  },
  {
    id: 'light',
    label: 'Light',
    needsOs: false,
    description: 'A light, low-detail map using the Positron style.',
    coverage: 'Worldwide · OpenFreeMap',
  },
  {
    id: 'satellite',
    label: 'Satellite',
    needsOs: false,
    description: 'Cloudless Sentinel-2 imagery from 2024. Not live imagery.',
    coverage: 'Worldwide · EOX',
  },
  {
    id: 'hybrid',
    label: 'Hybrid',
    needsOs: false,
    description: '2024 satellite imagery with roads, borders and place labels.',
    coverage: 'Worldwide · EOX / OpenFreeMap',
  },
  {
    id: 'os_road',
    label: 'OS Road',
    needsOs: true,
    description: 'Roads and settlements from Ordnance Survey.',
    coverage: 'Great Britain · zoom 7–16',
  },
  {
    id: 'os_outdoor',
    label: 'OS Outdoor',
    needsOs: true,
    description: 'Terrain and outdoor features from Ordnance Survey.',
    coverage: 'Great Britain · zoom 7–16',
  },
  {
    id: 'os_light',
    label: 'OS Light',
    needsOs: true,
    description: 'A subdued Ordnance Survey map for data overlays.',
    coverage: 'Great Britain · zoom 7–16',
  },
] as const satisfies readonly BaseLayerOption[];

export const DARK_STYLE_URL = 'https://tiles.openfreemap.org/styles/dark';

/** Imagery and OS rasters retain the dark style for their surrounding map and hybrid labels. */
export function vectorStyleFor(layer: BaseLayer): string {
  if (layer === 'streets') return 'https://tiles.openfreemap.org/styles/liberty';
  if (layer === 'light') return 'https://tiles.openfreemap.org/styles/positron';
  return DARK_STYLE_URL;
}

export const RASTER_SOURCE_ID = 'ase-base-raster';
export const RASTER_LAYER_ID = 'ase-base-raster';

export const EOX_TILES =
  'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg';
export const EOX_ATTRIBUTION =
  '<a href="https://s2maps.eu">Sentinel-2 cloudless</a> by ' +
  '<a href="https://eox.at">EOX IT Services GmbH</a> ' +
  '(<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>), ' +
  'contains modified Copernicus Sentinel data 2024';
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
