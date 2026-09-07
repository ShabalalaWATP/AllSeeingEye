import {
  RASTER_LAYER_ID,
  RASTER_SOURCE_ID,
  hidesVectorLabels,
  rasterSourceFor,
} from './baseLayers';
import type { BaseLayer } from './baseLayers';
import type { Map as MapLibreMap, SkySpecification } from 'maplibre-gl';

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

export function applyRasterLayer(map: MapLibreMap, baseLayer: BaseLayer): void {
  if (map.getLayer(RASTER_LAYER_ID) !== undefined) map.removeLayer(RASTER_LAYER_ID);
  if (map.getSource(RASTER_SOURCE_ID) !== undefined) map.removeSource(RASTER_SOURCE_ID);
  const layers = map.getStyle().layers;
  const source = rasterSourceFor(baseLayer);
  if (source !== null) {
    map.addSource(RASTER_SOURCE_ID, source);
    // Under boundaries and labels, above the flat land and water fills.
    const above = layers.find((layer) => layer.type === 'line' || layer.type === 'symbol');
    map.addLayer({ id: RASTER_LAYER_ID, type: 'raster', source: RASTER_SOURCE_ID }, above?.id);
  }
  const visibility = hidesVectorLabels(baseLayer) ? 'none' : 'visible';
  for (const layer of layers) {
    if (layer.type === 'symbol' || layer.type === 'line') {
      map.setLayoutProperty(layer.id, 'visibility', visibility);
    }
  }
}
