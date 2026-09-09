import { expect, it } from 'vitest';
import { drawingReducer, initialDrawingState } from './drawingState';
import type { Position } from './geoJsonTypes';

it('rejects invalid circle radii atomically without breaking a subsequent render', () => {
  let state = drawingReducer(initialDrawingState, { type: 'shape', shape: 'circle' });
  state = drawingReducer(state, { type: 'picking', picking: true });
  state = drawingReducer(state, { type: 'add', lon: 0, lat: 0 });
  state = drawingReducer(state, { type: 'add', lon: 30, lat: 0 });
  expect(state.anchors).toHaveLength(1);
  expect(state.error).toMatch(/radius/);
  state = drawingReducer(state, { type: 'add', lon: 0.1, lat: 0 });
  expect(state.anchors).toHaveLength(2);
  expect(state.picking).toBe(false);
  expect(drawingReducer(state, { type: 'add', lon: 0.2, lat: 0 })).toBe(state);
  expect(drawingReducer(state, { type: 'clear' }).anchors).toHaveLength(0);
});

function dragState(interaction: 'drag' | 'move' = 'drag') {
  return {
    ...initialDrawingState,
    shape: 'rectangle' as const,
    anchors: [
      [0, 0],
      [2, 2],
    ] as Position[],
    interaction,
    picking: true,
  };
}
const drag = (
  phase: 'start' | 'move' | 'end' | 'cancel',
  current: Position,
  start: Position = [1, 1],
) => ({ type: 'drag' as const, phase, start, current, tolerance: 0.01 });
it('previews a replacement, cancels without changing committed points, then commits release', () => {
  const original = dragState();
  let state = drawingReducer(original, drag('start', [1, 1]));
  state = drawingReducer(state, drag('move', [3, 3]));
  expect(state.preview).toEqual([
    [1, 1],
    [3, 3],
  ]);
  expect(state.anchors).toEqual(original.anchors);
  state = drawingReducer(state, drag('cancel', [3, 3]));
  expect(state.preview).toBeNull();
  expect(state.anchors).toEqual(original.anchors);
  state = drawingReducer(state, drag('start', [1, 1]));
  state = drawingReducer(state, drag('end', [4, 5]));
  expect(state.anchors).toEqual([
    [1, 1],
    [4, 5],
  ]);
  expect(state.picking).toBe(false);
});
it('only moves a hit sketch and keeps committed geometry after cancellation or invalid release', () => {
  const original = dragState('move');
  let state = drawingReducer(original, drag('start', [10, 10], [10, 10]));
  expect(state.dragStart).toBeNull();
  expect(state.error).toMatch(/inside/);
  state = drawingReducer(state, drag('start', [1, 1]));
  state = drawingReducer(state, drag('move', [2, 3]));
  expect(state.preview).toEqual([
    [1, 2],
    [3, 4],
  ]);
  state = drawingReducer(state, drag('cancel', [2, 3]));
  expect(state.anchors).toEqual(original.anchors);
  state = drawingReducer(state, drag('start', [1, 1]));
  state = drawingReducer(state, drag('end', [2, 3]));
  expect(state.anchors).toEqual([
    [1, 2],
    [3, 4],
  ]);
  state = drawingReducer(dragState(), drag('start', [1, 1]));
  state = drawingReducer(state, drag('end', [1, 1]));
  expect(state.error).toMatch(/width and height/);
  expect(state.anchors).toEqual(original.anchors);
});
it('undo and tool changes discard previews, and clear retains drag creation mode', () => {
  let state = drawingReducer(dragState(), drag('start', [1, 1]));
  state = drawingReducer(state, drag('move', [3, 3]));
  expect(drawingReducer(state, { type: 'undo' }).preview).toBeNull();
  expect(drawingReducer(state, { type: 'picking', picking: false }).dragStart).toBeNull();
  expect(drawingReducer(state, { type: 'interaction', interaction: 'move' }).preview).toBeNull();
  expect(drawingReducer(state, { type: 'clear' }).interaction).toBe('drag');
});
