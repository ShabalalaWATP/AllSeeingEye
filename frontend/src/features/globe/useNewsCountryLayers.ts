import { useCallback, useMemo } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { ViewMode } from '@/stores/globe';
import { zoomForBounds } from '@/lib/api/geo';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { NewsCountryContext, useNewsCountryContext } from './useNewsCountryContext';
import { newsCountryLayers } from './layers/newsCountries';

export function useNewsCountryLayers(
  state: ReturnType<typeof useNewsCountryContext>,
  event: LiveEvent | null,
  engine: GlobeEngineHandle,
  closeOthers: () => void,
  picking: boolean,
  mode: ViewMode,
) {
  const select = state.select;
  const focus = useCallback(
    (group: NewsCountryContext) => {
      if (picking) return;
      closeOthers();
      select(group.country.iso2);
      engine.flyTo({ center: group.country.centroid, zoom: zoomForBounds(group.country.bounds) });
    },
    [picking, closeOthers, select, engine],
  );
  return useMemo(
    () =>
      newsCountryLayers(
        state.groups,
        state.selected ??
          state.groups.find((group) => group.events.some((item) => item.id === event?.id)) ??
          null,
        focus,
        mode === 'map',
        !picking,
      ),
    [state.groups, state.selected, event?.id, focus, mode, picking],
  );
}
