import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Position } from '@/lib/map/geoJsonTypes';
import { measurementPaths } from '@/lib/map/measurements';
import type { MeasurementMode } from '@/lib/map/measurements';

export function measurementLayers(
  points: readonly Position[],
  mode: MeasurementMode,
  flat: boolean,
): Layer[] {
  if (!points.length) return [];
  const paths = measurementPaths(points, mode).flatMap((path) => {
    let current: Position[] = [];
    const pieces: Position[][] = [current];
    for (const point of path) {
      if (flat && Math.abs(point[1]) > 85.05112878) {
        current = [];
        pieces.push(current);
      } else current.push(point);
    }
    return pieces.filter((piece) => piece.length > 1);
  });
  return [
    new PathLayer<Position[]>({
      id: 'measurement-path',
      data: paths,
      getPath: (path) => path,
      getColor: [220, 250, 255, 240],
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: true,
    }),
    ...measurementPointLayers(points, flat),
  ];
}

/** Reusable handles do not calculate or allocate a discarded geodesic path. */
export function measurementPointLayers(points: readonly Position[], flat: boolean): Layer[] {
  if (!points.length) return [];
  return [
    new ScatterplotLayer<Position>({
      id: 'measurement-points',
      data: points.filter((point) => !flat || Math.abs(point[1]) <= 85.05112878),
      getPosition: (point) => point,
      getRadius: 8,
      radiusUnits: 'pixels',
      getFillColor: [120, 225, 240, 255],
      stroked: true,
      getLineColor: [5, 8, 10, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
    }),
    new TextLayer<{ point: Position; label: string }>({
      id: 'measurement-labels',
      data: points
        .map((point, index) => ({ point, label: String(index + 1) }))
        .filter(({ point }) => !flat || Math.abs(point[1]) <= 85.05112878),
      getPosition: (item) => item.point,
      getText: (item) => item.label,
      getSize: 12,
      getColor: [4, 10, 14, 255],
      fontWeight: 'bold',
      billboard: true,
      pickable: false,
    }),
  ];
}
