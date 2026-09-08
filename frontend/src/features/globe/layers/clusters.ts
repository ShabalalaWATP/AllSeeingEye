/**
 * Low-zoom clustering: located events are binned on a unit sphere per category so the
 * globe shows a few sized circles with counts instead of thousands of overlapping dots.
 */
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';

import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

import { CATEGORY_STYLES } from '@/lib/categories';

/** Below this zoom the globe clusters; above it every event is its own marker. */
export const CLUSTER_ZOOM = 3;
/** Cells with fewer events than this stay individual markers. */
export const CLUSTER_MIN = 3;

export interface Cluster {
  id: string;
  category: Category;
  lon: number;
  lat: number;
  count: number;
  maxSeverity: number;
  members?: readonly LiveEvent[];
}

export interface Clustered {
  clusters: Cluster[];
  loose: LiveEvent[];
}

/** Nominal angular cell width: coarser when further out. */
export function cellSizeFor(zoom: number): number {
  const bucket = clusteringZoomFor(zoom);
  return bucket === 0 ? 12 : bucket === 1.5 ? 6 : 3;
}

/** A stable zoom within each grouping, including the unclustered view. */
export function clusteringZoomFor(zoom: number): number {
  return zoom < 1.5 ? 0 : zoom < 2.5 ? 1.5 : zoom < CLUSTER_ZOOM ? 2.5 : CLUSTER_ZOOM;
}

interface SphericalCell {
  category: Category;
  members: LiveEvent[];
  x: number;
  y: number;
  z: number;
}

/**
 * Quantised unit-vector bins avoid the date-line seam and collapsing polar longitude cells.
 * This is bounded grid aggregation, not a radius-neighbour search: nearby points
 * on opposite cell boundaries can still occupy different bins. The centre is the
 * normalised vector mean, never an arithmetic longitude mean across the date line.
 */
export function clusterEvents(events: readonly LiveEvent[], cellDegrees: number): Clustered {
  if (!Number.isFinite(cellDegrees) || cellDegrees <= 0 || cellDegrees > 30)
    throw new RangeError('Cluster angular width must be greater than zero and at most 30 degrees.');
  const radians = Math.PI / 180;
  const step = 2 * Math.sin((cellDegrees * radians) / 2);
  const cells = new Map<string, SphericalCell>();
  for (const event of events) {
    if (event.point === null) continue;
    const lon = event.point.lon * radians;
    const lat = event.point.lat * radians;
    const x = Math.cos(lat) * Math.cos(lon);
    const y = Math.cos(lat) * Math.sin(lon);
    const z = Math.sin(lat);
    const key = `${event.category}:${Math.round(x / step)}:${Math.round(y / step)}:${Math.round(z / step)}`;
    const cell = cells.get(key) ?? { category: event.category, members: [], x: 0, y: 0, z: 0 };
    cell.members.push(event);
    cell.x += x;
    cell.y += y;
    cell.z += z;
    cells.set(key, cell);
  }
  const clusters: Cluster[] = [];
  const loose: LiveEvent[] = [];
  for (const [key, cell] of cells) {
    if (cell.members.length < CLUSTER_MIN) {
      loose.push(...cell.members);
      continue;
    }
    const count = cell.members.length;
    const horizontal = Math.hypot(cell.x, cell.y);
    const longitude = horizontal / count < 1e-12 ? 0 : Math.atan2(cell.y, cell.x) / radians;
    clusters.push({
      id: key,
      category: cell.category,
      lon: Math.abs(longitude) > 180 - 1e-10 ? -180 : longitude,
      lat: Math.atan2(cell.z, horizontal) / radians,
      count,
      members: cell.members,
      maxSeverity: Math.max(...cell.members.map((event) => event.severity ?? 0)),
    });
  }
  return { clusters, loose };
}

/** Circle radius in pixels from the member count; grows slowly so hubs do not swallow the map. */
export function clusterRadius(count: number): number {
  return 10 + Math.min(26, Math.log2(count) * 4);
}

export interface ClusterPick {
  object?: Cluster;
}

/** A circle per cluster and a count label, in the category colour. */
export function buildClusterLayers(
  clusters: readonly Cluster[],
  onPick: (cluster: Cluster) => void,
): Layer[] {
  if (clusters.length === 0) return [];
  return [
    new ScatterplotLayer<Cluster>({
      id: 'clusters',
      data: clusters,
      pickable: true,
      radiusUnits: 'pixels',
      stroked: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 1,
      getPosition: (cluster) => [cluster.lon, cluster.lat],
      getRadius: (cluster) => clusterRadius(cluster.count),
      getFillColor: (cluster) => [...CATEGORY_STYLES[cluster.category].colour, 150],
      getLineColor: (cluster) => [...CATEGORY_STYLES[cluster.category].colour, 255],
      onClick: (info: ClusterPick) => {
        if (info.object !== undefined) onPick(info.object);
        return true;
      },
    }),
    new TextLayer<Cluster>({
      id: 'cluster-labels',
      data: clusters,
      getPosition: (cluster) => [cluster.lon, cluster.lat],
      getText: (cluster) => String(cluster.count),
      getSize: 12,
      sizeUnits: 'pixels',
      getColor: [233, 228, 220, 255],
      fontFamily: 'ui-monospace, monospace',
      fontWeight: 600,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'center',
    }),
  ];
}
