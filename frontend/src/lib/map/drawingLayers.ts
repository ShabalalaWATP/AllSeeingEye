import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import type { MeasurementMode } from './measurements';
import { measurementLayers } from './measurementLayers';

/** Separate IDs allow an ordinary measurement and a drawing to coexist. */
export function drawingLayers(points: readonly Position[], mode: MeasurementMode, flat: boolean) {
  return measurementLayers(points, mode, flat).map(
    (layer) => layer.clone({ id: `drawing-${layer.id}` }) as Layer,
  );
}
