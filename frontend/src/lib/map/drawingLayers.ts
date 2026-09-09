import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import type { MeasurementMode } from './measurements';
import { measurementLayers, measurementPointLayers } from './measurementLayers';
import { PolygonLayer } from '@deck.gl/layers';

/** Separate IDs allow an ordinary measurement and a drawing to coexist. */
export function drawingLayers(
  points: readonly Position[],
  mode: MeasurementMode,
  flat: boolean,
  anchors: readonly Position[] = points,
) {
  const outline = measurementLayers(points, mode, flat)
    .filter((layer) => layer.id === 'measurement-path')
    .map((layer) => layer.clone({ id: `drawing-${layer.id}` }) as Layer);
  // Circle handles are its centre/radius anchors, not all 32 sampled perimeter vertices.
  const handles = measurementPointLayers(anchors, flat).map(
    (layer) => layer.clone({ id: `drawing-${layer.id}` }) as Layer,
  );
  // Tessellate a continuous longitude ring, avoiding a fill across most of the
  // Earth when the sketch crosses the dateline. Deck splits wrapped flat maps.
  const ring = points.map((point) => [...point] as Position);
  for (const [i, vertex] of ring.entries()) {
    const previous = ring[i - 1];
    if (previous)
      vertex[0] = previous[0] + (((((vertex[0] - previous[0] + 180) % 360) + 360) % 360) - 180);
  }
  const fill =
    mode === 'area' &&
    points.length >= 3 &&
    (!flat || points.every((point) => Math.abs(point[1]) <= 85))
      ? [
          new PolygonLayer<readonly Position[]>({
            id: 'drawing-fill',
            data: [ring],
            getPolygon: (polygon) => polygon,
            getFillColor: [121, 216, 235, 36],
            stroked: false,
            pickable: false,
            wrapLongitude: flat,
          }),
        ]
      : [];
  return [...fill, ...outline, ...handles];
}
