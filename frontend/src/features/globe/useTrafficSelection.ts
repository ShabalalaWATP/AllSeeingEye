import { useCallback } from 'react';
import type { LiveEvent, Category } from '@/lib/api/eventSchemas';
import type { MapFocus } from '@/lib/map/MapEngine';
import type { ObservationKind, ObservationVisibility } from './ObservationControls';

/** A list selection enables its overlay, then uses the same inspector/highlight as a map pick. */
export function useTrafficSelection(
  engine: MapFocus,
  choose: (event: LiveEvent | null) => void,
  visibility: ObservationVisibility,
  toggle: (kind: ObservationKind) => void,
  hidden: readonly Category[],
  toggleCategory: (category: Category) => void,
) {
  return useCallback(
    (event: LiveEvent) => {
      const kind = event.category === 'aviation' ? 'aircraft' : 'vessels';
      if (!visibility[kind]) toggle(kind);
      if (hidden.includes(event.category)) toggleCategory(event.category);
      choose(event);
      if (event.point) engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: 5 });
    },
    [engine, choose, visibility, toggle, hidden, toggleCategory],
  );
}
