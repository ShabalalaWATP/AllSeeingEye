import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Camera } from '@/lib/api/cameras';
import type { MapBounds } from '@/lib/map/MapEngine';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import type { useCameras } from './useCameras';
import { buildCameraLayers } from './cameraLayers';
import { clusterCameras, type CameraCluster } from './cameraClusters';

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
    if (!cameras.enabled) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = engine.onView(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const next = {
          zoom: Math.floor(engine.getZoom()),
          bounds: engine.getViewportBounds?.() ?? null,
        };
        setView((previous) =>
          previous.zoom === next.zoom &&
          JSON.stringify(previous.bounds) === JSON.stringify(next.bounds)
            ? previous
            : next,
        );
      }, 150);
    });
    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, [engine, cameras.enabled]);
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
  const prepared = useMemo(
    () => clusterCameras(cameras.visible, view.zoom, cameras.selected?.id ?? null, view.bounds),
    [cameras.visible, cameras.selected?.id, view],
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
        prepared,
      ),
    [cameras.visible, cameras.selected?.id, selectCamera, mode, view, expandCluster, prepared],
  );
  return { focusCamera, cameraLayers };
}
