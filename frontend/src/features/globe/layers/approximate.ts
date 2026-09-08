import { ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES } from '@/lib/categories';

/** Screen-sized rings with a subtle pickable interior denote approximation, never a claimed ground radius. */
export function buildApproximateLayer(
  events: readonly LiveEvent[],
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void,
  selectedId: string | null,
): Layer | null {
  if (!events.length) return null;
  return new ScatterplotLayer<LiveEvent>({
    id: 'approximate-events',
    data: events,
    pickable: true,
    filled: true,
    getFillColor: (event) => [...CATEGORY_STYLES[event.category].colour, 24],
    stroked: true,
    radiusUnits: 'pixels',
    lineWidthUnits: 'pixels',
    lineWidthMinPixels: 2,
    getPosition: (event) => [event.point?.lon ?? NaN, event.point?.lat ?? NaN],
    getRadius: (event) => (event.id === selectedId ? 14 : 10),
    getLineColor: (event) =>
      event.id === selectedId
        ? [255, 255, 255, 255]
        : [...CATEGORY_STYLES[event.category].colour, 220],
    updateTriggers: { getRadius: [selectedId], getLineColor: [selectedId] },
    onClick: (info: { object?: LiveEvent; x?: number; y?: number }) => {
      if (typeof info.x === 'number' && typeof info.y === 'number')
        onPick(info.object ?? null, [info.x, info.y]);
      else onPick(info.object ?? null);
      return true;
    },
  });
}
