import type { Layer } from '@deck.gl/core';
import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';

import type {
  FrontlineKind,
  SpottedLoss,
  UkraineFrontline,
  UkraineSpotted,
} from '@/lib/api/ukraineMap';

type Rgba = [number, number, number, number];

/** Provider classes keep their own hues so they never read as the VIINA majority vote. */
export const FRONTLINE_RGB: Record<FrontlineKind, [number, number, number]> = {
  occupied: [244, 63, 94],
  liberated: [74, 222, 128],
  unknown: [203, 213, 225],
  historical: [168, 85, 247],
  line: [251, 191, 36],
};
export const SPOTTED_RGB: [number, number, number] = [251, 146, 60];

function colour(kind: FrontlineKind, alpha: number): Rgba {
  return [...FRONTLINE_RGB[kind], alpha];
}

/** Polygons as thin hatched outlines and lines as a bold stroke, all above the control areas. */
export function buildFrontlineLayers(frontline: UkraineFrontline | null): Layer[] {
  if (!frontline || frontline.features.length === 0) return [];
  const polygons = frontline.features.filter((feature) => feature.polygons.length > 0);
  const lines = frontline.features.filter((feature) => feature.lines.length > 0);
  const layers: Layer[] = [];
  if (polygons.length > 0)
    layers.push(
      new GeoJsonLayer({
        id: 'ukraine-frontline-areas',
        data: {
          type: 'FeatureCollection' as const,
          features: polygons.flatMap((feature) =>
            feature.polygons.map((polygon) => ({
              type: 'Feature' as const,
              properties: { kind: feature.kind, label: feature.label },
              geometry: { type: 'Polygon' as const, coordinates: polygon },
            })),
          ),
        },
        stroked: true,
        filled: true,
        getFillColor: (feature: { properties: { kind: FrontlineKind } }) =>
          colour(feature.properties.kind, 40),
        getLineColor: (feature: { properties: { kind: FrontlineKind } }) =>
          colour(feature.properties.kind, 240),
        getLineWidth: 2,
        lineWidthMinPixels: 2,
        pickable: false,
      }),
    );
  if (lines.length > 0)
    layers.push(
      new GeoJsonLayer({
        id: 'ukraine-frontline-lines',
        data: {
          type: 'FeatureCollection' as const,
          features: lines.flatMap((feature) =>
            feature.lines.map((line) => ({
              type: 'Feature' as const,
              properties: { kind: feature.kind, label: feature.label },
              geometry: { type: 'LineString' as const, coordinates: line },
            })),
          ),
        },
        stroked: true,
        filled: false,
        getLineColor: colour('line', 255),
        getLineWidth: 3,
        lineWidthMinPixels: 3,
        pickable: false,
      }),
    );
  return layers;
}

/** Geolocated confirmed losses as small pickable markers. */
export function buildSpottedLayer(
  spotted: UkraineSpotted | null,
  onHover: (loss: SpottedLoss | null, x: number, y: number) => void,
): Layer[] {
  if (!spotted || spotted.losses.length === 0) return [];
  return [
    new ScatterplotLayer<SpottedLoss>({
      id: 'ukraine-spotted-losses',
      data: spotted.losses,
      getPosition: (loss) => [loss.lon, loss.lat],
      getFillColor: [...SPOTTED_RGB, 210],
      getLineColor: [10, 14, 22, 200],
      stroked: true,
      getRadius: 600,
      radiusMinPixels: 2.5,
      radiusMaxPixels: 6,
      lineWidthMinPixels: 1,
      pickable: true,
      onHover: (info) => onHover((info.object as SpottedLoss | undefined) ?? null, info.x, info.y),
    }),
  ];
}
