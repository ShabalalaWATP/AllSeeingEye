import { drawingReducer, initialDrawingState } from './drawingState';

type State = typeof initialDrawingState;
export type DrawingHistoryAction =
  | Parameters<typeof drawingReducer>[1]
  | { type: 'history-undo' }
  | { type: 'redo' }
  | { type: 'reset' };
export const initialDrawingHistory = {
  current: initialDrawingState,
  past: [] as State[],
  future: [] as State[],
};
/** Store completed operations, never drag previews or pointer frames. */
export function drawingHistoryReducer(
  history: typeof initialDrawingHistory,
  action: DrawingHistoryAction,
): typeof initialDrawingHistory {
  if (action.type === 'reset') return initialDrawingHistory;
  if (action.type === 'history-undo') {
    const previous = history.past.at(-1);
    return previous
      ? {
          current: { ...previous, picking: false, preview: null, dragStart: null },
          past: history.past.slice(0, -1),
          future: [history.current, ...history.future].slice(0, 50),
        }
      : history;
  }
  if (action.type === 'redo') {
    const next = history.future[0];
    return next
      ? {
          current: { ...next, picking: false, preview: null, dragStart: null },
          past: [...history.past, history.current].slice(-50),
          future: history.future.slice(1),
        }
      : history;
  }
  const current = drawingReducer(history.current, action);
  const changed =
    current.shape !== history.current.shape ||
    JSON.stringify(current.anchors) !== JSON.stringify(history.current.anchors);
  return changed
    ? {
        current,
        past: [...history.past, { ...history.current, preview: null, dragStart: null }].slice(-50),
        future: [],
      }
    : { ...history, current };
}
