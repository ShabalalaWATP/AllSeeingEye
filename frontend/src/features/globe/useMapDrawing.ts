import { useEffect, useMemo, useReducer } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { drawingVertices } from '@/lib/map/drawingGeometry';
import type { DrawingShape } from '@/lib/map/drawingGeometry';
import { drawingReducer, initialDrawingState } from '@/lib/map/drawingState';
import { measurementText } from '@/lib/map/measurements';
import type { GlobeEngineHandle } from './useGlobeEngine';
export function useMapDrawing(engine: Pick<GlobeEngineHandle, 'onClick'>, enabled: boolean) {
  const [state, dispatch] = useReducer(drawingReducer, initialDrawingState);
  const { shape, anchors, picking, error } = state;
  const maximum = shape === 'circle' || shape === 'rectangle' ? 2 : 32;
  const active = picking && enabled && anchors.length < maximum;
  useEffect(
    () =>
      engine.onClick(({ lon, lat }) => {
        if (active) dispatch({ type: 'add', lon, lat });
      }),
    [engine, active],
  );
  useEffect(() => {
    const clear = () => dispatch({ type: 'clear' });
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (next.user?.id !== previous.user?.id) clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  const points = useMemo(() => drawingVertices(shape, anchors), [shape, anchors]);
  const mode = shape === 'path' ? ('distance' as const) : ('area' as const);
  return {
    shape,
    points,
    anchors,
    mode,
    picking: active,
    canPick: enabled,
    error,
    result: measurementText(points, mode),
    setPicking: (next: boolean) => dispatch({ type: 'picking', picking: next }),
    add: (lon: number, lat: number) => dispatch({ type: 'add', lon, lat }),
    setShape: (next: DrawingShape) => dispatch({ type: 'shape', shape: next }),
    undo: () => dispatch({ type: 'undo' }),
    clear: () => dispatch({ type: 'clear' }),
  };
}
export type MapDrawing = ReturnType<typeof useMapDrawing>;
