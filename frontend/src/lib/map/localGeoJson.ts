import type { LocalCollection, LocalFeature, LocalGeometry, Position } from './geoJsonTypes';
import { splitLine, topologyBudget, validatePolygon } from './geoJsonTopology';
export const MAX_GEOJSON_BYTES = 5 * 1024 * 1024;
export const MAX_GEOJSON_FEATURES = 2000;
export const MAX_GEOJSON_VERTICES = 100000;
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Expected a GeoJSON object.');
  const record = value as Record<string, unknown>;
  if ('crs' in record)
    throw new Error(
      'Only RFC7946 WGS84 longitude/latitude is supported. Remove or convert the declared CRS before import.',
    );
  return record;
}
function list(value: unknown, minimum = 1): unknown[] {
  if (!Array.isArray(value) || value.length < minimum || value.length > MAX_GEOJSON_VERTICES)
    throw new Error('Invalid or oversized geometry coordinates.');
  return value;
}
export function parseLocalGeoJson(
  text: string,
  profile: 'annotation' | 'source' = 'annotation',
  chargeTopology = topologyBudget(),
  chargeVertex: () => void = () => undefined,
): {
  canonical: LocalCollection;
  display: LocalCollection;
  vertices: number;
} {
  if (new TextEncoder().encode(text).byteLength > MAX_GEOJSON_BYTES)
    throw new Error('GeoJSON is limited to 5 MiB.');
  const root = object(JSON.parse(text) as unknown);
  if (root.type !== 'FeatureCollection') throw new Error('Import a GeoJSON FeatureCollection.');
  const features = list(root.features);
  if (features.length > MAX_GEOJSON_FEATURES)
    throw new Error('GeoJSON is limited to 2,000 features.');
  let vertices = 0;
  const point = (raw: unknown): Position => {
    const pos = list(raw, 2);
    if (
      pos.length !== 2 ||
      typeof pos[0] !== 'number' ||
      typeof pos[1] !== 'number' ||
      !Number.isFinite(pos[0]) ||
      !Number.isFinite(pos[1]) ||
      Math.abs(pos[0]) > 180 ||
      Math.abs(pos[1]) > 90
    )
      throw new Error(
        'Coordinates must be finite WGS84 longitude/latitude pairs. Altitude is not supported.',
      );
    if (++vertices > MAX_GEOJSON_VERTICES)
      throw new Error('GeoJSON is limited to 100,000 vertices.');
    chargeVertex();
    return [pos[0], pos[1]];
  };
  const line = (raw: unknown) => list(raw, 2).map(point);
  const polygon = (raw: unknown) => {
    const rings = list(raw).map(line);
    validatePolygon(rings, chargeTopology, profile);
    return rings;
  };
  const geometry = (raw: unknown): LocalGeometry => {
    const item = object(raw),
      c = item.coordinates;
    switch (item.type) {
      case 'Point':
        return { type: 'Point', coordinates: point(c) };
      case 'MultiPoint':
        return { type: 'MultiPoint', coordinates: list(c).map(point) };
      case 'LineString':
        return { type: 'LineString', coordinates: line(c) };
      case 'MultiLineString':
        return { type: 'MultiLineString', coordinates: list(c).map(line) };
      case 'Polygon':
        return { type: 'Polygon', coordinates: polygon(c) };
      case 'MultiPolygon':
        return { type: 'MultiPolygon', coordinates: list(c).map(polygon) };
      default:
        throw new Error(
          'Unsupported geometry. Use points, lines or polygons; GeometryCollection is not supported.',
        );
    }
  };
  const canonical: LocalCollection = {
    type: 'FeatureCollection',
    features: features.map((raw, id): LocalFeature => {
      const item = object(raw);
      if (item.type !== 'Feature') throw new Error('Every collection entry must be a Feature.');
      const props = item.properties == null ? {} : object(item.properties);
      const label =
        typeof props.name === 'string'
          ? props.name
          : typeof props.title === 'string'
            ? props.title
            : typeof props.label === 'string'
              ? props.label
              : `Feature ${id + 1}`;
      return {
        type: 'Feature',
        id,
        geometry: geometry(item.geometry),
        properties: { label: Array.from(label).slice(0, 300).join('') },
      };
    }),
  };
  const display: LocalCollection = {
    type: 'FeatureCollection',
    features: canonical.features.map((feature) => {
      const geo = feature.geometry;
      const adjusted: LocalGeometry =
        geo.type === 'LineString'
          ? { type: 'MultiLineString', coordinates: splitLine(geo.coordinates) }
          : geo.type === 'MultiLineString'
            ? { type: 'MultiLineString', coordinates: geo.coordinates.flatMap(splitLine) }
            : geo;
      return { ...feature, geometry: adjusted };
    }),
  };
  if (
    display.features.reduce((sum, feature) => sum + geometryVertices(feature.geometry), 0) >
    MAX_GEOJSON_VERTICES
  ) {
    throw new Error(
      'Antimeridian splitting exceeds the 100,000 display-vertex limit. Simplify the geometry.',
    );
  }
  return { canonical, display, vertices };
}

export function geometryIsPolar(geometry: LocalGeometry): boolean {
  const inspect = (positions: Position[]) =>
    positions.some((point) => Math.abs(point[1]) > 85.05112878);
  switch (geometry.type) {
    case 'Point':
      return inspect([geometry.coordinates]);
    case 'MultiPoint':
    case 'LineString':
      return inspect(geometry.coordinates);
    case 'Polygon':
    case 'MultiLineString':
      return geometry.coordinates.some(inspect);
    case 'MultiPolygon':
      return geometry.coordinates.some((polygon) => polygon.some(inspect));
  }
}

export function geometryVertices(geometry: LocalGeometry): number {
  switch (geometry.type) {
    case 'Point':
      return 1;
    case 'MultiPoint':
    case 'LineString':
      return geometry.coordinates.length;
    case 'Polygon':
    case 'MultiLineString':
      return geometry.coordinates.reduce((sum, line) => sum + line.length, 0);
    case 'MultiPolygon':
      return geometry.coordinates.reduce(
        (sum, polygon) => sum + polygon.reduce((count, line) => count + line.length, 0),
        0,
      );
  }
}
