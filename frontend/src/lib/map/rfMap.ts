import { Geodesic } from 'geographiclib-geodesic';
import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import { measurementPaths, measurementPoint } from './measurements';
import { calculateRf } from './rfPlanning';
import type { RfInputs } from './rfPlanning';

export interface RfMapEstimate {
  origin: Position;
  receiver: Position | null;
  radiusKm: number;
  horizonKm: number;
  sensitivityDistanceKm: number;
  label: string;
}

export function rfMapEstimate(
  input: RfInputs,
  origin: Position,
  receiver: Position | null = null,
): RfMapEstimate {
  measurementPoint(...origin);
  if (receiver) measurementPoint(...receiver);
  const result = calculateRf(input);
  const radiusKm = Math.min(result.horizonKm, result.sensitivityDistanceKm);
  if (radiusKm < 0.001)
    throw new Error(
      'The estimated radius is below 1 metre. Increase antenna heights or review the link inputs.',
    );
  return {
    origin,
    receiver,
    radiusKm,
    horizonKm: result.horizonKm,
    sensitivityDistanceKm: result.sensitivityDistanceKm,
    label: `RF estimate · ${radiusKm.toFixed(1)} km · no terrain model`,
  };
}

/** Fixed-size geodesic outline, not a filled claim of reception coverage. */
export function rfRangeRing(estimate: RfMapEstimate): Position[] {
  return Array.from({ length: 73 }, (_, index) => {
    const point = Geodesic.WGS84.Direct(
      estimate.origin[1],
      estimate.origin[0],
      index * 5,
      estimate.radiusKm * 1000,
    );
    return measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
  });
}

export function rfMapLayers(estimate: RfMapEstimate | null, flat: boolean): Layer[] {
  if (!estimate) return [];
  const ring = rfRangeRing(estimate);
  const paths = [
    ring,
    ...(estimate.receiver
      ? measurementPaths([estimate.origin, estimate.receiver], 'distance')
      : []),
  ];
  // Split at Web Mercator's latitude limit, preserving the globe geometry.
  const visiblePaths = paths.flatMap((path) => {
    const pieces: Position[][] = [[]];
    for (const point of path) {
      if (flat && Math.abs(point[1]) > 85.05112878) pieces.push([]);
      else pieces[pieces.length - 1]?.push(point);
    }
    return pieces.filter((piece) => piece.length > 1);
  });
  const points = [estimate.origin, ...(estimate.receiver ? [estimate.receiver] : [])].filter(
    (point) => !flat || Math.abs(point[1]) <= 85.05112878,
  );
  return [
    new PathLayer<Position[]>({
      id: 'rf-estimate-paths',
      data: visiblePaths,
      getPath: (path) => path,
      getColor: [195, 160, 255, 240],
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new ScatterplotLayer<Position>({
      id: 'rf-estimate-sites',
      data: points,
      getPosition: (point) => point,
      getRadius: 6,
      radiusUnits: 'pixels',
      getFillColor: [195, 160, 255, 255],
      pickable: false,
    }),
    new TextLayer<{ point: Position; label: string }>({
      id: 'rf-estimate-label',
      data:
        points.length && points[0] === estimate.origin
          ? [{ point: estimate.origin, label: estimate.label }]
          : [],
      getPosition: (item) => item.point,
      getText: (item) => item.label,
      getSize: 12,
      getColor: [225, 210, 255, 255],
      getPixelOffset: [0, -20],
      background: true,
      getBackgroundColor: [8, 8, 16, 220],
      pickable: false,
    }),
  ];
}
