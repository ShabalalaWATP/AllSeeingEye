import { ScatterplotLayer } from '@deck.gl/layers';
import type { LiveEvent } from '@/lib/api/eventSchemas';

/** Selection is a screen-space cursor, not a claimed geographic radius. */
export function buildSelectionLayer(event: LiveEvent) {
  return new ScatterplotLayer<LiveEvent>({
    id: 'selected-event-halo',
    data: [event],
    pickable: false,
    filled: false,
    stroked: true,
    radiusUnits: 'pixels',
    lineWidthUnits: 'pixels',
    getRadius: 21,
    getLineWidth: 3,
    getLineColor: [255, 255, 255, 255],
    getPosition: (item) => [item.point?.lon ?? NaN, item.point?.lat ?? NaN],
  });
}
