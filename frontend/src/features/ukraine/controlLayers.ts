import type { Layer } from '@deck.gl/core';
import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';

import type { ControlStatus, UkraineControl, Settlement } from '@/lib/api/ukraine';

type Rgba = [number, number, number, number];

/** Series colours: cyan Ukraine, ember Russia, amber contested, muted unknown. */
export const STATUS_RGB: Record<ControlStatus, [number, number, number]> = {
  ua: [56, 189, 248],
  ru: [239, 108, 72],
  contested: [252, 211, 77],
  unknown: [148, 163, 184],
};

export const UKRAINE_BOUNDS = { west: 22, south: 44, east: 40.5, north: 52.5 };

function fill(status: ControlStatus, alpha: number): Rgba {
  return [...STATUS_RGB[status], alpha];
}

function collection(polygons: number[][][][], status: ControlStatus, name = '') {
  return {
    type: 'FeatureCollection' as const,
    features: polygons.map((polygon) => ({
      type: 'Feature' as const,
      properties: { status, name },
      geometry: { type: 'Polygon' as const, coordinates: polygon },
    })),
  };
}

/** Reported control areas, oblast outlines and frontline-zone settlements, in draw order. */
export function buildControlLayers(
  control: UkraineControl,
  onHover: (settlement: Settlement | null, x: number, y: number) => void,
): Layer[] {
  const areas = control.areas.map(
    (area) =>
      new GeoJsonLayer({
        id: `ukraine-control-${area.status}`,
        data: collection(area.polygons, area.status),
        stroked: true,
        filled: true,
        getFillColor: fill(area.status, area.status === 'contested' ? 110 : 70),
        getLineColor: fill(area.status, 220),
        getLineWidth: 1,
        lineWidthMinPixels: 1,
        pickable: false,
      }),
  );
  const outlines = new GeoJsonLayer({
    id: 'ukraine-oblast-outlines',
    data: {
      type: 'FeatureCollection' as const,
      features: control.outlines.flatMap(
        (outline) => collection(outline.polygons, 'unknown', outline.name).features,
      ),
    },
    stroked: true,
    filled: false,
    getLineColor: [226, 232, 240, 90],
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    pickable: false,
  });
  const settlements = new ScatterplotLayer<Settlement>({
    id: 'ukraine-settlements',
    data: control.settlements,
    getPosition: (row) => [row.lon, row.lat],
    getFillColor: (row) => fill(row.status, row.status === 'ua' ? 170 : 230),
    getRadius: 400,
    radiusMinPixels: 1.5,
    radiusMaxPixels: 5,
    pickable: true,
    onHover: (info) => onHover((info.object as Settlement | undefined) ?? null, info.x, info.y),
  });
  return [...areas, outlines, settlements];
}
