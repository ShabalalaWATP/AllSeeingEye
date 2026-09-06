/** Local-only geometry, never an API payload or a shared live event. */
export type Position = [number, number];
export type LocalGeometry =
  | { type: 'Point'; coordinates: Position }
  | { type: 'MultiPoint' | 'LineString'; coordinates: Position[] }
  | { type: 'MultiLineString' | 'Polygon'; coordinates: Position[][] }
  | { type: 'MultiPolygon'; coordinates: Position[][][] };
export interface LocalFeature {
  type: 'Feature';
  id: number;
  geometry: LocalGeometry;
  properties: { label: string };
}
export interface LocalCollection {
  type: 'FeatureCollection';
  features: LocalFeature[];
}
export interface LocalOverlay {
  canonical: LocalCollection;
  display: LocalCollection;
  vertices: number;
  source: string;
  datasetDate: string;
  attribution: string;
  precision: 'exact' | 'approximate' | 'unknown';
}
