import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import { Geodesic } from 'geographiclib-geodesic';
import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import type { HfSkywaveResult } from './hfSkywave';
import { measurementPoint } from './measurements';

export interface HfSkywaveMapEstimate {
  origin: Position;
  frequencyMHz: number;
  scenario: HfSkywaveResult;
}

/** Two bounded range outlines. No filled reception claim and no perpetual animation. */
export function hfSkywaveLayers(estimate: HfSkywaveMapEstimate | null, flat: boolean): Layer[] {
  if (!estimate?.scenario.compatible) return [];
  measurementPoint(...estimate.origin);
  const { innerRadiusKm, outerRadiusKm } = estimate.scenario;
  const rings = [innerRadiusKm, outerRadiusKm].flatMap((radius) => {
    if (radius === null || !Number.isFinite(radius) || radius < 0.001 || radius > 10000) return [];
    const pieces: Position[][] = [[]];
    for (let index = 0; index <= 72; index++) {
      const point = Geodesic.WGS84.Direct(
        estimate.origin[1],
        estimate.origin[0],
        index * 5,
        radius * 1000,
      );
      const position = measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
      if (flat && Math.abs(position[1]) > 85.05112878) pieces.push([]);
      else pieces[pieces.length - 1]?.push(position);
    }
    return pieces.filter((piece) => piece.length > 1);
  });
  const sites = !flat || Math.abs(estimate.origin[1]) <= 85.05112878 ? [estimate.origin] : [];
  return [
    new PathLayer<Position[]>({
      id: 'hf-skywave-scenario-rings',
      data: rings,
      getPath: (path) => path,
      getColor: [160, 160, 255, 230],
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new ScatterplotLayer<Position>({
      id: 'hf-skywave-scenario-site',
      data: sites,
      getPosition: (point) => point,
      getRadius: 6,
      radiusUnits: 'pixels',
      getFillColor: [160, 160, 255, 255],
      pickable: false,
    }),
    new TextLayer<Position>({
      id: 'hf-skywave-scenario-label',
      data: sites,
      getPosition: (point) => point,
      getText: () =>
        `HF ${estimate.frequencyMHz.toFixed(1)} MHz · single-hop scenario · no forecast`,
      getSize: 12,
      getColor: [220, 220, 255, 255],
      getPixelOffset: [0, -20],
      background: true,
      getBackgroundColor: [8, 8, 16, 220],
      pickable: false,
    }),
  ];
}
