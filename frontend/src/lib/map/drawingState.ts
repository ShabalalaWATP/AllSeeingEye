import type { Position } from './geoJsonTypes';
import { drawingVertices } from './drawingGeometry';
import type { DrawingShape } from './drawingGeometry';
import { measurementPoint } from './measurements';
export const initialDrawingState = {
  shape: 'polygon' as DrawingShape,
  anchors: [] as Position[],
  picking: false,
  error: null as string | null,
};
type Action =
  | { type: 'add'; lon: number; lat: number }
  | { type: 'shape'; shape: DrawingShape }
  | { type: 'picking'; picking: boolean }
  | { type: 'undo' }
  | { type: 'clear' };
/** Atomic updates validate two map clicks delivered in the same render batch. */
export function drawingReducer(
  state: typeof initialDrawingState,
  action: Action,
): typeof initialDrawingState {
  if (action.type === 'clear') return { ...initialDrawingState, shape: state.shape };
  if (action.type === 'shape') return { ...initialDrawingState, shape: action.shape };
  if (action.type === 'picking') return { ...state, picking: action.picking };
  if (action.type === 'undo') return { ...state, anchors: state.anchors.slice(0, -1), error: null };
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
