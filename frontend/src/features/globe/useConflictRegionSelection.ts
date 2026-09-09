import { useCallback, useMemo } from 'react';
import { zoomForBounds } from '@/lib/api/geo';
import type { ViewMode } from '@/stores/globe';
import type { useConflictRegions } from './useConflictRegions';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { ConflictRegion } from './conflictRegions';
import { conflictRegionLayers } from './layers/conflictRegions';

export function useConflictRegionSelection(
  regions: ReturnType<typeof useConflictRegions>,
  enabled: boolean,
  picking: boolean,
  closeOthers: () => void,
  engine: GlobeEngineHandle,
  mode: ViewMode,
) {
  const { select } = regions;
  const focus = useCallback(
    (region: ConflictRegion) => {
      if (picking || !enabled || !regions.showRegions) return;
      closeOthers();
      select(region);
      engine.flyTo({ center: region.centre, zoom: zoomForBounds(region.bounds) });
    },
    [picking, enabled, regions.showRegions, closeOthers, select, engine],
  );
  const layers = useMemo(
    () =>
      enabled && regions.showRegions
        ? conflictRegionLayers(regions.filtered, regions.selected, focus, mode === 'map', !picking)
        : [],
    [enabled, regions.showRegions, regions.filtered, regions.selected, focus, mode, picking],
  );
  return { focus, layers };
}
