import type { Position } from './geoJsonTypes';
import { drawingVertices } from './drawingGeometry';
import type { DrawingShape } from './drawingGeometry';
import { measurementPoint } from './measurements';
import { hitsDrawing, moveDrawing } from './drawingMove';
export type DrawingInteraction = 'click' | 'drag' | 'move';
export const initialDrawingState = {
  shape: 'polygon' as DrawingShape,
  anchors: [] as Position[],
  picking: false,
  error: null as string | null,
  interaction: 'click' as DrawingInteraction,
  preview: null as Position[] | null,
  dragStart: null as Position | null,
};
type Action =
  | { type: 'add'; lon: number; lat: number }
  | { type: 'shape'; shape: DrawingShape }
  | { type: 'picking'; picking: boolean }
  | { type: 'undo' }
  | { type: 'clear' };
interface DragAction {
  type: 'drag';
  phase: 'start' | 'move' | 'end' | 'cancel';
  start: Position;
  current: Position;
  tolerance: number;
}
/** Atomic updates validate two map clicks delivered in the same render batch. */
export function drawingReducer(
  state: typeof initialDrawingState,
  action: Action | DragAction | { type: 'interaction'; interaction: DrawingInteraction },
): typeof initialDrawingState {
  if (action.type === 'clear')
    return {
      ...initialDrawingState,
      shape: state.shape,
      interaction: state.interaction === 'move' ? 'click' : state.interaction,
    };
  if (action.type === 'shape') return { ...initialDrawingState, shape: action.shape };
  if (action.type === 'interaction')
    return {
      ...state,
      interaction: action.interaction,
      picking: false,
      preview: null,
      dragStart: null,
      error: null,
    };
  if (action.type === 'picking')
    return { ...state, picking: action.picking, preview: null, dragStart: null };
  if (action.type === 'drag') {
    if (action.phase === 'cancel') return { ...state, preview: null, dragStart: null };
    if (!state.picking || state.interaction === 'click') return state;
    if (action.phase === 'start') {
      if (
        state.interaction === 'move' &&
        !hitsDrawing(state.shape, state.anchors, action.start, action.tolerance)
      )
        return { ...state, error: 'Start the drag inside your shape or near its line.' };
      return { ...state, dragStart: action.start, preview: null, error: null };
    }
    if (!state.dragStart) return state;
    try {
      const anchors =
        state.interaction === 'move'
          ? moveDrawing(state.shape, state.anchors, state.dragStart, action.current)
          : [measurementPoint(...state.dragStart), measurementPoint(...action.current)];
      if (
        state.shape === 'rectangle' &&
        anchors[0] &&
        anchors[1] &&
        (anchors[0][0] === anchors[1][0] || anchors[0][1] === anchors[1][1])
      )
        throw new Error('Drag to a different corner to give the rectangle width and height.');
      drawingVertices(state.shape, anchors);
      return action.phase === 'end'
        ? { ...state, anchors, preview: null, dragStart: null, picking: false, error: null }
        : { ...state, preview: anchors, error: null };
    } catch (error) {
      return action.phase === 'end'
        ? {
            ...state,
            preview: null,
            dragStart: null,
            error: error instanceof Error ? error.message : 'Invalid shape.',
          }
        : state;
    }
  }
  if (action.type === 'undo')
    return {
      ...state,
      anchors: state.anchors.slice(0, -1),
      preview: null,
      dragStart: null,
      error: null,
    };
  const maximum = state.shape === 'circle' || state.shape === 'rectangle' ? 2 : 32;
  if (state.anchors.length >= maximum) return state;
  try {
    const anchors = [...state.anchors, measurementPoint(action.lon, action.lat)];
    drawingVertices(state.shape, anchors);
    return { ...state, anchors, error: null, picking: state.picking && anchors.length < maximum };
  } catch (caught) {
    return { ...state, error: caught instanceof Error ? caught.message : 'Invalid drawing point.' };
  }
}
