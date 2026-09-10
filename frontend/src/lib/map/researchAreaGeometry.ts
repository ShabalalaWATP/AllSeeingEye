import { boundsFromCorners, rectangleArea } from './areaGeometry';
import { drawingVertices, type DrawingShape } from './drawingGeometry';
import type { LocalCollection, Position } from './geoJsonTypes';
import { parseLocalGeoJson } from './localGeoJson';

/** The collection boundary is a polygon, never a substituted bounding envelope. */
export function researchAreaGeometry(
  shape: DrawingShape,
  anchors: readonly Position[],
): LocalCollection {
  if (shape === 'path') throw new Error('Choose a polygon, rectangle or circle for research.');
  if (anchors.length < (shape === 'polygon' ? 3 : 2))
    throw new Error(
      shape === 'polygon' ? 'Add at least three corners.' : 'Draw the complete area first.',
    );
  if (shape === 'rectangle') {
    const [first, second] = anchors;
    if (!first || !second) throw new Error('Choose two opposite corners.');
    return rectangleArea(boundsFromCorners(first, second));
  }
  const points = drawingVertices(shape, anchors);
  const first = points[0];
  if (!first) throw new Error('Draw the complete area first.');
  const ring = [...points, first];
  if (
    ring.some((point, i) => {
      const previous = ring[i - 1];
      return previous !== undefined && Math.abs(point[0] - previous[0]) > 180;
    })
  )
    throw new Error('For an area crossing 180° longitude, use a rectangle.');
  return parseLocalGeoJson(
    JSON.stringify({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { label: 'Research area' },
          geometry: { type: 'Polygon', coordinates: [ring] },
        },
      ],
    }),
  ).canonical;
}
