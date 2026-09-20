import { drawingVertices, type DrawingShape } from './drawingGeometry';
import { measurementPoint } from './measurements';
import type { Position } from './geoJsonTypes';
import { topologyBudget, validatePolygon } from './geoJsonTopology';

export interface DrawingObject {
  id: string;
  name: string;
  shape: DrawingShape | 'point';
  anchors: Position[];
  colour: string;
  visible: boolean;
  locked: boolean;
  notes: string;
}
export interface DrawingCollection {
  version: 1;
  objects: DrawingObject[];
  selectedId: string | null;
}
export const emptyDrawingCollection: DrawingCollection = {
  version: 1,
  objects: [],
  selectedId: null,
};
const record = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Expected a drawing object.');
  return value as Record<string, unknown>;
};
const boundedText = (value: unknown, limit: number, label: string) => {
  if (typeof value !== 'string' || value.length > limit) throw new Error(`Invalid ${label}.`);
  return value;
};
export function validateDrawingObject(value: unknown): DrawingObject {
  const item = record(value);
  const shape = item.shape as DrawingObject['shape'];
  if (!['point', 'path', 'polygon', 'rectangle', 'circle'].includes(shape))
    throw new Error('Unsupported drawing shape.');
  if (!Array.isArray(item.anchors)) throw new Error('Drawing anchors are required.');
  const anchors = item.anchors.map((point: unknown) => {
    if (!Array.isArray(point) || point.length !== 2 || point.some((n) => typeof n !== 'number'))
      throw new Error('Use longitude/latitude coordinate pairs.');
    return measurementPoint(point[0] as number, point[1] as number);
  });
  const minimum = shape === 'point' ? 1 : shape === 'polygon' ? 3 : 2;
  const maximum = shape === 'point' ? 1 : shape === 'circle' || shape === 'rectangle' ? 2 : 32;
  if (anchors.length < minimum || anchors.length > maximum)
    throw new Error(
      `This shape needs ${minimum}${minimum === maximum ? '' : ` to ${maximum}`} anchors.`,
    );
  if (shape !== 'point') drawingVertices(shape, anchors);
  const [first, second] = anchors;
  if (!first) throw new Error('Missing geometry.');
  if (shape === 'polygon') validatePolygon([[...anchors, first]], topologyBudget(), 'annotation');
  if (shape === 'rectangle' && second && (first[0] === second[0] || first[1] === second[1]))
    throw new Error('Rectangle needs width and height.');
  if (typeof item.colour !== 'string' || !/^#[\da-f]{6}$/i.test(item.colour))
    throw new Error('Use a six-digit colour.');
  if (typeof item.visible !== 'boolean' || typeof item.locked !== 'boolean')
    throw new Error('Invalid drawing visibility or lock.');
  const id = boundedText(item.id, 80, 'drawing ID');
  const name = boundedText(item.name, 120, 'drawing name').trim();
  if (!id || !name) throw new Error('A drawing needs an ID and name.');
  return {
    id,
    name,
    shape,
    anchors,
    colour: item.colour,
    visible: item.visible,
    locked: item.locked,
    notes: boundedText(item.notes, 2000, 'drawing notes'),
  };
}
export function validateDrawingCollection(value: unknown): DrawingCollection {
  const data = record(value);
  if (data.version !== 1 || !Array.isArray(data.objects) || data.objects.length > 50)
    throw new Error('Use a version 1 collection with at most 50 drawings.');
  const objects = data.objects.map(validateDrawingObject);
  if (new Set(objects.map((item) => item.id)).size !== objects.length)
    throw new Error('Drawing IDs must be unique.');
  if (data.selectedId !== null && !objects.some((item) => item.id === data.selectedId))
    throw new Error('Unknown selected drawing.');
  return { version: 1, objects, selectedId: data.selectedId as string | null };
}
export function newDrawingObject(
  shape: DrawingObject['shape'],
  anchors: Position[],
  index: number,
): DrawingObject {
  return validateDrawingObject({
    id: crypto.randomUUID(),
    name: `${shape === 'point' ? 'Point' : 'Drawing'} ${index + 1}`,
    shape,
    anchors,
    colour: '#79d8eb',
    visible: true,
    locked: false,
    notes: '',
  });
}
export function exportDrawingGeoJson(collection: DrawingCollection): string {
  return JSON.stringify(
    {
      type: 'FeatureCollection',
      features: collection.objects.map((item) => {
        const points =
          item.shape === 'point' ? item.anchors : drawingVertices(item.shape, item.anchors);
        const geometry =
          item.shape === 'point'
            ? { type: 'Point', coordinates: points[0] }
            : item.shape === 'path'
              ? { type: 'LineString', coordinates: points }
              : { type: 'Polygon', coordinates: [[...points, points[0]]] };
        return {
          type: 'Feature',
          id: item.id,
          geometry,
          properties: { name: item.name, colour: item.colour, notes: item.notes },
        };
      }),
    },
    null,
    2,
  );
}
/** Import a deliberately small GeoJSON subset, without remote URLs, holes or geometry guessing. */
export function importDrawingGeoJson(text: string): DrawingCollection {
  if (new TextEncoder().encode(text).length > 128 * 1024)
    throw new Error('GeoJSON must be at most 128 KiB.');
  const input = record(JSON.parse(text));
  if (
    input.type !== 'FeatureCollection' ||
    !Array.isArray(input.features) ||
    input.features.length > 50 ||
    input.crs !== undefined
  )
    throw new Error('Use a WGS84 FeatureCollection with at most 50 features.');
  const objects = input.features.map((value, index) => {
    const feature = record(value);
    if (feature.type !== 'Feature') throw new Error('Expected GeoJSON features.');
    const geometry = record(feature.geometry);
    const properties = feature.properties == null ? {} : record(feature.properties);
    let shape: DrawingObject['shape'];
    let anchors: unknown;
    if (geometry.type === 'Point') {
      shape = 'point';
      anchors = [geometry.coordinates];
    } else if (geometry.type === 'LineString') {
      shape = 'path';
      anchors = geometry.coordinates;
    } else if (geometry.type === 'Polygon') {
      shape = 'polygon';
      if (
        !Array.isArray(geometry.coordinates) ||
        geometry.coordinates.length !== 1 ||
        !Array.isArray(geometry.coordinates[0])
      )
        throw new Error('Polygon holes are not supported.');
      const ring = geometry.coordinates[0];
      if (ring.length < 4 || JSON.stringify(ring[0]) !== JSON.stringify(ring.at(-1)))
        throw new Error('Polygon rings must be closed.');
      anchors = ring.slice(0, -1);
    } else throw new Error('Supported geometry: Point, LineString and Polygon.');
    return validateDrawingObject({
      id: crypto.randomUUID(),
      name: properties.name ?? properties.label ?? `Imported ${index + 1}`,
      shape,
      anchors,
      colour: properties.colour ?? '#79d8eb',
      notes: properties.notes ?? '',
      visible: true,
      locked: false,
    });
  });
  return { version: 1, objects, selectedId: null };
}
