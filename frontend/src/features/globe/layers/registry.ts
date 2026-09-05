/**
 * The layer registry: one style per category, shared by the globe layers, the
 * layer panel legend and event cards, so a colour means the same thing everywhere.
 */
import { ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';

import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

import { CLUSTER_ZOOM, buildClusterLayers, cellSizeFor, clusterEvents } from './clusters';
import type { Cluster } from './clusters';
import { buildIconLayer, iconFor } from './icons';

export interface CategoryStyle {
  label: string;
  colour: [number, number, number];
  css: string;
  order: number;
}

export const CATEGORY_STYLES: Record<Category, CategoryStyle> = {
  disaster: { label: 'Disasters', colour: [255, 111, 55], css: '#ff6f37', order: 0 },
  conflict: { label: 'Conflict', colour: [255, 90, 90], css: '#ff5a5a', order: 1 },
  news: { label: 'News', colour: [233, 228, 220], css: '#e9e4dc', order: 2 },
  aviation: { label: 'Aviation', colour: [245, 181, 63], css: '#f5b53f', order: 3 },
  maritime: { label: 'Maritime', colour: [92, 211, 155], css: '#5cd39b', order: 4 },
  space: { label: 'Space', colour: [167, 139, 250], css: '#a78bfa', order: 5 },
  cyber: { label: 'Cyber', colour: [34, 211, 238], css: '#22d3ee', order: 6 },
  social: { label: 'Social', colour: [244, 114, 182], css: '#f472b6', order: 7 },
  political: { label: 'Political', colour: [148, 163, 184], css: '#94a3b8', order: 8 },
  humanitarian: { label: 'Humanitarian', colour: [251, 191, 36], css: '#fbbf24', order: 9 },
  economic: { label: 'Economic', colour: [110, 231, 183], css: '#6ee7b7', order: 10 },
};

export const ORDERED_CATEGORIES = (Object.keys(CATEGORY_STYLES) as Category[]).sort(
  (a, b) => CATEGORY_STYLES[a].order - CATEGORY_STYLES[b].order,
);

const MIN_RADIUS_PX = 3;
const MAX_RADIUS_PX = 12;

/** Marker radius in pixels from severity (0 to 1), with a floor so everything is clickable. */
export function radiusFor(event: LiveEvent): number {
  const severity = Math.min(1, Math.max(0, event.severity ?? 0.2));
  return MIN_RADIUS_PX + severity * (MAX_RADIUS_PX - MIN_RADIUS_PX);
}

export interface PickInfo {
  object?: LiveEvent;
}

/** The camera's zoom and what to do when a cluster is picked; absent means no clustering. */
export interface LayerView {
  zoom: number;
  onCluster: (cluster: Cluster) => void;
}

function scatterLayers(
  events: readonly LiveEvent[],
  onPick: (event: LiveEvent | null) => void,
  selectedId: string | null,
): Layer[] {
  const byCategory = new Map<Category, LiveEvent[]>();
  for (const event of events) {
    const bucket = byCategory.get(event.category) ?? [];
    bucket.push(event);
    byCategory.set(event.category, bucket);
  }
  return [...byCategory.entries()].map(([category, data]) => {
    const style = CATEGORY_STYLES[category];
    return new ScatterplotLayer<LiveEvent>({
      id: `events-${category}`,
      data,
      pickable: true,
      radiusUnits: 'pixels',
      stroked: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 1,
      getPosition: (event) => [event.point?.lon ?? 0, event.point?.lat ?? 0],
      getRadius: (event) => (event.id === selectedId ? radiusFor(event) + 4 : radiusFor(event)),
      getFillColor: (event) => [...style.colour, event.id === selectedId ? 255 : 190],
      getLineColor: (event) => (event.id === selectedId ? [255, 255, 255, 255] : [7, 7, 11, 200]),
      updateTriggers: {
        getRadius: [selectedId],
        getFillColor: [selectedId],
        getLineColor: [selectedId],
      },
      onClick: (info: PickInfo) => {
        onPick(info.object ?? null);
        return true;
      },
    });
  });
}

/**
 * The data layers for the visible, located events: clusters when the camera is far out,
 * otherwise icons for aircraft, cyclones and volcanoes and severity-sized points for
 * everything else. Toggling a category never rebuilds the others.
 */
export function buildEventLayers(
  events: readonly LiveEvent[],
  hidden: readonly Category[],
  onPick: (event: LiveEvent | null) => void,
  selectedId: string | null,
  view?: LayerView,
): Layer[] {
  const visible = events.filter(
    (event) => event.point !== null && !hidden.includes(event.category),
  );
  let loose: LiveEvent[] = visible;
  const layers: Layer[] = [];
  if (view !== undefined && view.zoom < CLUSTER_ZOOM) {
    const clustered = clusterEvents(visible, cellSizeFor(view.zoom));
    layers.push(...buildClusterLayers(clustered.clusters, view.onCluster));
    loose = clustered.loose;
  }
  layers.push(
    ...scatterLayers(
      loose.filter((event) => iconFor(event) === null),
      onPick,
      selectedId,
    ),
  );
  const icons = buildIconLayer(loose, onPick, selectedId);
  if (icons !== null) layers.push(icons);
  return layers;
}
