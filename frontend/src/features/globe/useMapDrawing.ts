import { useEffect, useMemo, useReducer } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { drawingVertices } from '@/lib/map/drawingGeometry';
import type { DrawingShape } from '@/lib/map/drawingGeometry';
import { type DrawingInteraction } from '@/lib/map/drawingState';
import { drawingHistoryReducer, initialDrawingHistory } from '@/lib/map/drawingHistory';
import type { Position } from '@/lib/map/geoJsonTypes';
import { drawingAuthority } from '@/lib/map/drawingAuthority';
import { measurementText } from '@/lib/map/measurements';
import type { GlobeEngineHandle } from './useGlobeEngine';
export function useMapDrawing(
  engine: Pick<GlobeEngineHandle, 'onClick'> &
    Partial<Pick<GlobeEngineHandle, 'onDrag' | 'getZoom'>>,
  enabled: boolean,
) {
  const [history, dispatch] = useReducer(drawingHistoryReducer, initialDrawingHistory);
  const state = history.current;
  const { shape, anchors, picking, error, interaction } = state;
  const maximum = shape === 'circle' || shape === 'rectangle' ? 2 : 32;
  const active = picking && enabled && (interaction !== 'click' || anchors.length < maximum);
  useEffect(
    () =>
      engine.onClick(({ lon, lat }) => {
        if (active && interaction === 'click') dispatch({ type: 'add', lon, lat });
      }),
    [engine, active, interaction],
  );
  useEffect(
    () =>
      engine.onDrag?.((event) => {
        if (!active) return;
        dispatch({
          type: 'drag',
          ...event,
          start: [event.start.lon, event.start.lat],
          current: [event.current.lon, event.current.lat],
          tolerance: (12 * 360) / (512 * 2 ** (engine.getZoom?.() ?? 4)),
        });
      }),
    [engine, active],
  );
  useEffect(() => {
    const clear = () => dispatch({ type: 'reset' });
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (drawingAuthority(next) !== drawingAuthority(previous)) clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  const displayedAnchors = state.preview ?? anchors;
  const points = useMemo(() => drawingVertices(shape, displayedAnchors), [shape, displayedAnchors]);
  const mode = shape === 'path' ? ('distance' as const) : ('area' as const);
  return {
    shape,
    points,
    anchors,
    displayedAnchors,
    interaction,
    canDrag: engine.onDrag !== undefined,
    mode,
    picking: active,
    canPick: enabled,
    error,
    result: measurementText(points, mode),
    setPicking: (next: boolean) => dispatch({ type: 'picking', picking: next }),
    setInteraction: (next: DrawingInteraction) =>
      dispatch({ type: 'interaction', interaction: next }),
    add: (lon: number, lat: number) => dispatch({ type: 'add', lon, lat }),
    setShape: (next: DrawingShape) => {
      dispatch({ type: 'shape', shape: next });
      if (engine.onDrag && (next === 'circle' || next === 'rectangle'))
        dispatch({ type: 'interaction', interaction: 'drag' });
    },
    undo: () => dispatch({ type: 'history-undo' }),
    redo: () => dispatch({ type: 'redo' }),
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
    load: (shape: DrawingShape, anchors: Position[]) => dispatch({ type: 'load', shape, anchors }),
    clear: () => dispatch({ type: 'clear' }),
    reset: () => dispatch({ type: 'reset' }),
  };
}
export type MapDrawing = ReturnType<typeof useMapDrawing>;
