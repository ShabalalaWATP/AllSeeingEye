import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Camera } from '@/lib/api/cameras';
import type { MapBounds } from '@/lib/map/MapEngine';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import type { useCameras } from './useCameras';
import { buildCameraLayers } from './cameraLayers';
import type { CameraCluster } from './cameraClusters';

/** Keep camera focus, event deselection and measurement gestures consistent. */
export function useCameraSelection(
  cameras: ReturnType<typeof useCameras>,
  picking: boolean,
  close: () => void,
  engine: GlobeEngineHandle,
  mode: ViewMode,
) {
  const [view, setView] = useState<{ zoom: number; bounds: MapBounds | null }>({
    zoom: 1,
    bounds: null,
  });
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = engine.onView(() => {
      clearTimeout(timer);
      timer = setTimeout(
        () =>
          setView({
            zoom: Math.floor(engine.getZoom()),
            bounds: engine.getViewportBounds?.() ?? null,
          }),
        150,
      );
    });
    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, [engine]);
  const expandCluster = useCallback(
    (cluster: CameraCluster) => {
      if (!picking)
        engine.flyTo({
          center: [cluster.longitude, cluster.latitude],
          zoom: Math.min(18, engine.getZoom() + 2),
        });
    },
    [engine, picking],
  );
  const selectPublicCamera = cameras.select;
  const selectCamera = useCallback(
    (camera: Camera) => {
      if (picking) return;
      close();
      selectPublicCamera(camera);
    },
    [picking, close, selectPublicCamera],
  );
  const focusCamera = useCallback(
    (camera: Camera) => {
      selectCamera(camera);
      if (!picking) engine.flyTo({ center: [camera.longitude, camera.latitude], zoom: 13 });
    },
    [selectCamera, picking, engine],
  );
  const cameraLayers = useMemo(
    () =>
      buildCameraLayers(
        cameras.visible,
        selectCamera,
        cameras.selected?.id ?? null,
        mode === 'globe',
        view.zoom,
        expandCluster,
        view.bounds,
      ),
    [cameras.visible, cameras.selected?.id, selectCamera, mode, view, expandCluster],
  );
  return { focusCamera, cameraLayers };
}
