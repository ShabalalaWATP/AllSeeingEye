/**
 * Low-zoom clustering: located events are binned into grid cells per category so the
 * globe shows a few sized circles with counts instead of thousands of overlapping dots.
 */
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';

import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

import { CATEGORY_STYLES } from './registry';

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
}

export interface Clustered {
  clusters: Cluster[];
  loose: LiveEvent[];
}

/** Cell size in degrees for a zoom level: coarser when further out. */
export function cellSizeFor(zoom: number): number {
  return zoom < 1.5 ? 12 : zoom < 2.5 ? 6 : 3;
}

/** Bins located events into cells; cells with enough events become clusters. */
export function clusterEvents(events: readonly LiveEvent[], cellDegrees: number): Clustered {
  const cells = new Map<string, { category: Category; members: LiveEvent[] }>();
  for (const event of events) {
    if (event.point === null) continue;
    const col = Math.floor(event.point.lon / cellDegrees);
    const row = Math.floor(event.point.lat / cellDegrees);
    const key = `${event.category}:${String(col)}:${String(row)}`;
    const cell = cells.get(key) ?? { category: event.category, members: [] };
    cell.members.push(event);
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
    clusters.push({
      id: key,
      category: cell.category,
      lon: cell.members.reduce((sum, event) => sum + (event.point?.lon ?? 0), 0) / count,
      lat: cell.members.reduce((sum, event) => sum + (event.point?.lat ?? 0), 0) / count,
      count,
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
