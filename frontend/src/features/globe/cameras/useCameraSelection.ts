import { useCallback, useMemo } from 'react';
import type { Camera } from '@/lib/api/cameras';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import type { useCameras } from './useCameras';
import { buildCameraLayers } from './cameraLayers';

/** Keep camera focus, event deselection and measurement gestures consistent. */
export function useCameraSelection(
  cameras: ReturnType<typeof useCameras>,
  picking: boolean,
  close: () => void,
  engine: GlobeEngineHandle,
  mode: ViewMode,
) {
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
      ),
    [cameras.visible, cameras.selected?.id, selectCamera, mode],
  );
  return { focusCamera, cameraLayers };
}
