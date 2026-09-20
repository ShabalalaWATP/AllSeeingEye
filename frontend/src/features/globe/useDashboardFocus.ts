import { useCallback } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import type { MapFocus } from '@/lib/map/MapEngine';
import { isMappedEvent } from './geographicPrecision';

/** Catalogue and context picks share navigation but keep their evidence scopes separate. */
export function useDashboardFocus({
  engine,
  picking,
  hidden,
  toggleCategory,
  choose,
  close,
  chooseContext,
}: {
  engine: MapFocus;
  picking: boolean;
  hidden: readonly Category[];
  toggleCategory: (category: Category) => void;
  choose: (event: LiveEvent | null) => void;
  close: () => void;
  chooseContext: (event: LiveEvent) => void;
}) {
  const selectContext = useCallback(
    (event: LiveEvent) => {
      if (picking) return;
      close();
      chooseContext(event);
      if (isMappedEvent(event) && event.point)
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: 5 });
    },
    [picking, close, chooseContext, engine],
  );
  const selectSatellite = useCallback(
    (event: LiveEvent) => {
      if (picking) return;
      if (hidden.includes('space')) toggleCategory('space');
      choose(event);
      if (isMappedEvent(event) && event.point)
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: 4 });
    },
    [picking, hidden, toggleCategory, choose, engine],
  );
  return { selectContext, selectSatellite };
}
