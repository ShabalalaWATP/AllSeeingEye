import { useCallback, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { MapCamera, MapEngine, MapRenderStatus } from '@/lib/map/MapEngine';

export interface MapRenderState {
  status: MapRenderStatus;
  message: string;
}

/** Only an explicit operator action replaces the complete map instance. */
export function useMapRecovery(engine: RefObject<MapEngine | null>) {
  const [renderState, setRenderState] = useState<MapRenderState>({ status: 'ready', message: '' });
  const [revision, setRevision] = useState(0);
  const camera = useRef<MapCamera | null>(null);
  const onRenderStatus = useCallback((status: MapRenderStatus, message: string) => {
    setRenderState((previous) =>
      previous.status === status && previous.message === message ? previous : { status, message },
    );
  }, []);
  const reload = useCallback(() => {
    camera.current = engine.current?.getCamera() ?? null;
    onRenderStatus('recovering', 'Reloading the map graphics.');
    setRevision((value) => value + 1);
  }, [engine, onRenderStatus]);
  const restoreReloadCamera = useCallback((next: MapEngine) => {
    if (camera.current) next.restoreCamera(camera.current);
    camera.current = null;
  }, []);
  return { renderState, revision, reload, onRenderStatus, restoreReloadCamera };
}
