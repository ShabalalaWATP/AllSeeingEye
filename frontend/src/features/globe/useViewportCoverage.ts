import { useEffect } from 'react';
import { useEventsStore } from '@/stores/events';
import type { CoverageBounds } from '@/stores/events.geography';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Fetch only after the camera settles; one bounded mirror is shared by both projections. */
export function useViewportCoverage(engine: GlobeEngineHandle, enabled: boolean): void {
  const { getZoom, getViewportBounds, onView } = engine;
  useEffect(() => {
    if (!enabled) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const update = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const view = getViewportBounds?.();
        const bounds: CoverageBounds | null =
          view && getZoom() >= 2 ? [view.west, view.south, view.east, view.north] : null;
        const store = useEventsStore.getState();
        if (JSON.stringify(bounds) === JSON.stringify(store.coverageBounds)) return;
        store.setCoverageBounds(bounds);
        void store.load();
      }, 800);
    };
    update();
    const off = onView(update);
    return () => {
      clearTimeout(timer);
      off();
    };
  }, [enabled, getZoom, getViewportBounds, onView]);
  useEffect(() => () => useEventsStore.getState().setCoverageBounds(null), []);
}
