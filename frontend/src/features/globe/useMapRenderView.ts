import { useCallback, useMemo, useSyncExternalStore } from 'react';
import type { ViewMode } from '@/stores/globe';
import { CLUSTER_ZOOM, clusteringZoomFor } from './layers/clusters';
import type { GlobeEngineHandle } from './useGlobeEngine';

interface RenderView {
  zoom: number;
  symbolMode: ViewMode;
}

/** Deck's globe becomes Mercator above zoom 12, independently of clustering. */
export function useMapRenderView(
  { getZoom, onView }: Pick<GlobeEngineHandle, 'getZoom' | 'onView'>,
  mode: ViewMode,
): RenderView {
  const subscribe = useCallback((notify: () => void) => onView(notify), [onView]);
  const getSnapshot = useCallback(() => {
    const actualZoom = getZoom();
    // A primitive snapshot stays equal during pans and zooms inside each band.
    return actualZoom > 12 ? 'close' : clusteringZoomFor(actualZoom);
  }, [getZoom]);
  const band = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return useMemo(
    () => ({
      zoom: band === 'close' ? CLUSTER_ZOOM : band,
      symbolMode: mode === 'globe' && band !== 'close' ? 'globe' : 'map',
    }),
    [band, mode],
  );
}
