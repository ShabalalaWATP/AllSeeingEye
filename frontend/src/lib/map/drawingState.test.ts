import { expect, it } from 'vitest';
import { drawingReducer, initialDrawingState } from './drawingState';

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
