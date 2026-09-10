/** Convert a bounded sketch to an explicitly rectangular indicator scope. */
import { Geodesic } from 'geographiclib-geodesic';
import { validateAreaBounds } from './areaGeometry';
import { drawingVertices } from './drawingGeometry';
import type { DrawingShape } from './drawingGeometry';
import type { Position } from './geoJsonTypes';
import type { MapBounds } from './MapEngine';
import { measure, measurementPaths } from './measurements';

export interface WatchAreaInput {
  bounds: MapBounds;
  source: 'rectangle' | 'sketch-envelope' | 'viewport';
}

export function drawingWatchArea(
  shape: DrawingShape,
  anchors: readonly Position[],
): WatchAreaInput {
  if (shape === 'path') throw new Error('Choose an area shape to watch. Paths have no area.');
  if (anchors.length > 32) throw new Error('A sketch may contain at most 32 anchors.');
  const points = drawingVertices(shape, anchors);
  if (shape === 'rectangle' && anchors.length !== 2)
    throw new Error('Finish the rectangle with two opposite corners.');
  if ((shape === 'circle' && anchors.length !== 2) || points.length < 3)
    throw new Error('Finish an area sketch before watching it.');
  if ((measure(points, 'area').squareMetres ?? 0) <= 0)
    throw new Error('Choose a sketch with a non-zero area.');

  // Rectangle sketches also have geodesic edges, which can bow beyond their corner
  // latitudes. Every drawn area therefore needs a sampled, conservative envelope.
  const paths = measurementPaths(points, 'area');
  const samples = paths.flat();
  const longitudes = samples.map(([lon]) => lon).sort((a, b) => a - b);
  let gapIndex = longitudes.length - 1;
  let gap = 360 + (longitudes[0] ?? NaN) - (longitudes[gapIndex] ?? NaN);
  for (let index = 0; index < longitudes.length - 1; index++) {
    const nextGap = (longitudes[index + 1] ?? NaN) - (longitudes[index] ?? NaN);
    if (nextGap > gap) {
      gap = nextGap;
      gapIndex = index;
    }
  }
  if (360 - gap >= 180) throw new Error('Choose a smaller area spanning less than half the world.');
  let west = longitudes[(gapIndex + 1) % longitudes.length] ?? NaN;
  let east = longitudes[gapIndex] ?? NaN;
  let south = Math.min(...samples.map((point) => point[1]));
  let north = Math.max(...samples.map((point) => point[1]));

  // A conservative half-sample-distance margin encloses the geodesic edges between
  // samples. The minimum WGS84 curvature radius bounds latitude and longitude travel.
  let longestStep = 0;
  for (const path of paths)
    for (let index = 1; index < path.length; index++) {
      const a = path[index - 1],
        b = path[index];
      if (!a || !b) continue;
      longestStep = Math.max(
        longestStep,
        Geodesic.WGS84.Inverse(a[1], a[0], b[1], b[0]).s12 ?? NaN,
      );
    }
  const latitudeMargin = (longestStep / 2 / 6_335_000) * (180 / Math.PI) + 1e-7;
  south -= latitudeMargin;
  north += latitudeMargin;
  const highestLatitude = Math.max(Math.abs(south), Math.abs(north));
  if (highestLatitude >= 89) throw new Error('Use explicit bounds for an area near a pole.');
  const longitudeMargin = latitudeMargin / Math.cos((highestLatitude * Math.PI) / 180);
  if (360 - gap + 2 * longitudeMargin >= 180)
    throw new Error('Choose a smaller area spanning less than half the world.');
  const wrap = (value: number) => ((value + 540) % 360) - 180;
  west = wrap(west - longitudeMargin);
  east = wrap(east + longitudeMargin);
  return { bounds: validateAreaBounds({ west, east, south, north }), source: 'sketch-envelope' };
}
