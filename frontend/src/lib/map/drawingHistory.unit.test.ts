import { expect, it } from 'vitest';
import { drawingHistoryReducer as reduce, initialDrawingHistory } from './drawingHistory';

it('undoes and redoes a complete move and clear without recording preview frames', () => {
  let history = reduce(initialDrawingHistory, {
    type: 'load',
    shape: 'rectangle',
    anchors: [
      [0, 0],
      [2, 2],
    ],
  });
  history = reduce(history, { type: 'interaction', interaction: 'move' });
  history = reduce(history, { type: 'picking', picking: true });
  const initialCount = history.past.length;
  history = reduce(history, {
    type: 'drag',
    phase: 'start',
    start: [1, 1],
    current: [1, 1],
    tolerance: 0.01,
  });
  history = reduce(history, {
    type: 'drag',
    phase: 'move',
    start: [1, 1],
    current: [2, 3],
    tolerance: 0.01,
  });
  expect(history.past.length).toBe(initialCount);
  history = reduce(history, {
    type: 'drag',
    phase: 'end',
    start: [1, 1],
    current: [2, 3],
    tolerance: 0.01,
  });
  expect(history.current.anchors).toEqual([
    [1, 2],
    [3, 4],
  ]);
  history = reduce(history, { type: 'history-undo' });
  expect(history.current.anchors).toEqual([
    [0, 0],
    [2, 2],
  ]);
  history = reduce(history, { type: 'redo' });
  expect(history.current.anchors).toEqual([
    [1, 2],
    [3, 4],
  ]);
  history = reduce(history, { type: 'clear' });
  expect(history.current.anchors).toEqual([]);
  history = reduce(history, { type: 'history-undo' });
  expect(history.current.anchors).toEqual([
    [1, 2],
    [3, 4],
  ]);
  expect(history.current.picking).toBe(false);
});
it('bounds history and irreversibly clears it on access reset', () => {
  let history = initialDrawingHistory;
  for (let i = 0; i < 80; i++)
    history = reduce(history, {
      type: 'load',
      shape: 'path',
      anchors: [
        [i, 0],
        [i + 1, 1],
      ],
    });
  expect(history.past).toHaveLength(50);
  history = reduce(history, { type: 'reset' });
  expect(reduce(history, { type: 'history-undo' })).toEqual(initialDrawingHistory);
});
it('drags one vertex atomically and rejects a drag away from handles', () => {
  let state = reduce(initialDrawingHistory, {
    type: 'load',
    shape: 'polygon',
    anchors: [
      [0, 0],
      [2, 0],
      [2, 2],
    ],
  });
  state = reduce(state, { type: 'interaction', interaction: 'vertex' });
  state = reduce(state, { type: 'picking', picking: true });
  state = reduce(state, {
    type: 'drag',
    phase: 'start',
    start: [1, 1],
    current: [1, 1],
    tolerance: 0.01,
  });
  expect(state.current.error).toMatch(/vertex handle/);
  state = reduce(state, {
    type: 'drag',
    phase: 'start',
    start: [2, 2],
    current: [2, 2],
    tolerance: 0.01,
  });
  state = reduce(state, {
    type: 'drag',
    phase: 'end',
    start: [2, 2],
    current: [3, 3],
    tolerance: 0.01,
  });
  expect(state.current.anchors).toEqual([
    [0, 0],
    [2, 0],
    [3, 3],
  ]);
  state = reduce(state, { type: 'history-undo' });
  expect(state.current.anchors).toEqual([
    [0, 0],
    [2, 0],
    [2, 2],
  ]);
});
