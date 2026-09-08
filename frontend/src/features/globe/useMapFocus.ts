import { useCallback } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import { isMappedEvent } from './geographicPrecision';
import type { GlobeEngineHandle } from './useGlobeEngine';

export const FOCUS_ZOOM = 4;

/** Move the map from evidence and nation lists, clearing unrelated inspection. */
export function useMapFocus(
  engine: GlobeEngineHandle,
  select: (id: string | null) => void,
  clearCamera: () => void,
  setCountry: (iso: string | null) => void,
  countryByIso: Record<string, Country>,
) {
  const focus = useCallback(
    (event: LiveEvent) => {
      clearCamera();
      select(event.id);
      if (event.point !== null && isMappedEvent(event)) {
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: FOCUS_ZOOM });
      }
    },
    [engine, select, clearCamera],
  );

  const changeNation = useCallback(
    (iso: string | null) => {
      setCountry(iso);
      const target = iso === null ? null : countryByIso[iso];
      if (target !== null && target !== undefined) {
        engine.flyTo({ center: target.centroid, zoom: zoomForBounds(target.bounds) });
      }
    },
    [countryByIso, engine, setCountry],
  );

  return { focus, changeNation };
}
