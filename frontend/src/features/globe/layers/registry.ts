/**
 * Builds map layers from live events using the shared category styles.
 */
import { ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import { sameLayerRows } from '@/lib/map/sameLayerRows';

import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { geographicOrder } from '@/stores/events.geography';
import { CATEGORY_STYLES } from '@/lib/categories';

import { isMappedEvent } from '../geographicPrecision';
import { buildApproximateLayer } from './approximate';
import { buildSelectionLayer } from './selection';

import { CLUSTER_ZOOM, buildClusterLayers, cellSizeFor, clusterEvents } from './clusters';
import type { Cluster } from './clusters';
import { buildIconLayer, iconFor } from './icons';

const MIN_RADIUS_PX = 3;
const MAX_RADIUS_PX = 12;

/** Marker radius in pixels from severity (0 to 1), with a floor so everything is clickable. */
export function radiusFor(event: LiveEvent): number {
  const severity = Math.min(1, Math.max(0, event.severity ?? 0.2));
  return MIN_RADIUS_PX + severity * (MAX_RADIUS_PX - MIN_RADIUS_PX);
}

export interface PickInfo {
  object?: LiveEvent;
  x?: number;
  y?: number;
}

/** The camera's zoom and what to do when a cluster is picked; absent means no clustering. */
export interface LayerView {
  globe?: boolean;
  zoom: number;
  onCluster: (cluster: Cluster) => void;
}

function scatterLayers(
  events: readonly LiveEvent[],
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void,
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
      dataComparator: sameLayerRows,
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
        if (typeof info.x === 'number' && typeof info.y === 'number')
          onPick(info.object ?? null, [info.x, info.y]);
        else onPick(info.object ?? null);
        return true;
      },
    });
  });
}

/**
 * The data layers for the visible, located events: clusters when the camera is far out,
 * otherwise icons for aircraft, cyclones and volcanoes and severity-sized points for
 * everything else.
 */
export function buildEventLayers(
  events: readonly LiveEvent[],
  hidden: readonly Category[],
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void,
  selectedId: string | null,
  view?: LayerView,
): Layer[] {
  const visible = events.filter(
    (event) => isMappedEvent(event) && !hidden.includes(event.category),
  );
  const exact = visible.filter((event) => event.geo_confidence === 'exact');
  const approximate = buildApproximateLayer(
    visible.filter((event) => event.geo_confidence !== 'exact'),
    onPick,
    selectedId,
  );
  let loose: LiveEvent[] = exact;
  const layers: Layer[] = approximate ? [approximate] : [];
  if (view !== undefined && view.zoom < CLUSTER_ZOOM) {
    // Keep a bounded sample of traffic recognisable at globe scale. Remaining
    // records still contribute to clusters, rather than disappearing.
    const traffic = exact.filter((event) =>
      ['aircraft', 'vessel', 'vessel_unknown'].includes(iconFor(event) ?? ''),
    );
    const shown = geographicOrder(traffic).slice(0, 250);
    const selectedTraffic = traffic.find((event) => event.id === selectedId);
    if (selectedTraffic && !shown.includes(selectedTraffic))
      shown[shown.length - 1] = selectedTraffic;
    const ids = new Set(shown.map((event) => event.id));
    const clustered = clusterEvents(
      exact.filter((event) => !ids.has(event.id)),
      cellSizeFor(view.zoom),
    );
    layers.push(...buildClusterLayers(clustered.clusters, view.onCluster));
    loose = [...shown, ...clustered.loose];
  }
  layers.push(
    ...scatterLayers(
      loose.filter((event) => iconFor(event) === null),
      onPick,
      selectedId,
    ),
  );
  // Approximate conflict reports retain their location ring and gain a type symbol.
  // They do not enter the exact-point cluster path or acquire more precise geography.
  const iconEvents = [
    ...loose,
    ...visible.filter((event) => event.category === 'conflict' && event.geo_confidence !== 'exact'),
  ];
  const icons = buildIconLayer(
    iconEvents,
    onPick,
    selectedId,
    Boolean(view?.globe && view.zoom <= 12),
  );
  if (icons !== null) layers.push(icons);
  const selected = visible.find((event) => event.id === selectedId);
  if (selected) layers.push(buildSelectionLayer(selected));
  return layers;
}
