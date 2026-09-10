import { GeoJsonLayer, PathLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import { researchAreaGeometry } from './researchAreaGeometry';
import { measurementPointLayers } from './measurementLayers';
import type { DrawingShape } from './drawingGeometry';
import type { Position } from './geoJsonTypes';

/** Render the same straight-coordinate edges that the collection predicates use. */
export function researchAreaLayers(
  shape: DrawingShape,
  anchors: readonly Position[],
  flat: boolean,
): Layer[] {
  if (!anchors.length) return [];
  const handles = measurementPointLayers(anchors, flat).map(
    (layer) => layer.clone({ id: `research-area-${layer.id}` }) as Layer,
  );
  try {
    const data = researchAreaGeometry(shape, anchors);
    return [
      new GeoJsonLayer({
        id: 'research-area-boundary',
        data,
        filled: true,
        stroked: true,
        getFillColor: [121, 216, 235, 30],
        getLineColor: [121, 216, 235, 245],
        getLineWidth: 2,
        lineWidthUnits: 'pixels',
        pickable: false,
        wrapLongitude: flat,
      }),
      ...handles,
    ];
  } catch {
    // An incomplete/invalid outline stays visible for correction, never filled as a valid area.
    return [
      new PathLayer<Position[]>({
        id: 'research-area-draft',
        data: [[...anchors]],
        getPath: (points) => points,
        getColor: [121, 216, 235, 200],
        getWidth: 2,
        widthUnits: 'pixels',
        pickable: false,
        wrapLongitude: flat,
      }),
      ...handles,
    ];
  }
}
