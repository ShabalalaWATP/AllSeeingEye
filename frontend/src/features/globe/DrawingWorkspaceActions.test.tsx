import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { useMapDrawing } from './useMapDrawing';
import { drawingHistoryReducer, initialDrawingHistory } from '@/lib/map/drawingHistory';
import { drawingReducer, initialDrawingState } from '@/lib/map/drawingState';

const engine = { onClick: () => () => undefined };
function setup() {
  return renderHook(() => {
    const drawing = useMapDrawing(engine, true);
    return { drawing, workspace: useDrawingWorkspace(drawing, true) };
  });
}
it('rejects stale object edits, safely handles stale selection and makes empty undo/redo harmless', () => {
  const { result } = setup();
  act(() => result.current.workspace.undo());
  act(() => result.current.workspace.redo());
  act(() => result.current.workspace.updateObject('missing', { name: 'Stale edit' }));
  expect(result.current.workspace.error).toContain('no longer exists');
  act(() => result.current.workspace.duplicate('missing'));
  act(() => result.current.workspace.remove('missing'));
  act(() => result.current.workspace.select('missing'));
  act(() => result.current.workspace.applySketch());
  expect(result.current.workspace.selected).toBeNull();
  expect(result.current.workspace.objects).toEqual([]);
  expect(drawingHistoryReducer(initialDrawingHistory, { type: 'redo' })).toEqual(
    initialDrawingHistory,
  );
});
it('protects locked metadata while allowing visibility changes and refuses to clear locked collections', () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([0, 0]));
  const id = result.current.workspace.selectedId ?? '';
  act(() => result.current.workspace.updateObject(id, { locked: true }));
  act(() => result.current.workspace.updateObject(id, { name: 'Changed' }));
  expect(result.current.workspace.error).toContain('Unlock');
  act(() => result.current.workspace.updateObject(id, { visible: false }));
  expect(result.current.workspace.selected?.visible).toBe(false);
  act(() => result.current.workspace.clearCollection());
  expect(result.current.workspace.objects).toHaveLength(1);
  expect(result.current.workspace.error).toContain('Unlock');
  act(() => result.current.workspace.updateObject(id, { locked: false }));
  act(() => result.current.workspace.clearCollection());
  expect(result.current.workspace.objects).toEqual([]);
  act(() => result.current.workspace.undo());
  expect(result.current.workspace.objects).toHaveLength(1);
});
it('updates selected path coordinates and leaves other objects intact, including hidden selection', () => {
  const { result } = setup();
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  act(() => result.current.workspace.addSketch());
  const id = result.current.workspace.selectedId ?? '';
  act(() => result.current.workspace.addPoint([4, 4]));
  act(() => result.current.workspace.select(id));
  act(() =>
    result.current.workspace.updateObject(id, {
      anchors: [
        [1, 1],
        [2, 2],
      ],
    }),
  );
  expect(result.current.drawing.anchors).toEqual([
    [1, 1],
    [2, 2],
  ]);
  expect(result.current.workspace.objects.at(-1)?.anchors).toEqual([[4, 4]]);
  act(() => result.current.workspace.updateObject(id, { visible: false }));
  act(() => result.current.workspace.select(id));
  expect(result.current.drawing.anchors).toEqual([]);
  act(() => result.current.workspace.remove(id));
  expect(result.current.workspace.selectedId).toBeNull();
  expect(result.current.workspace.objects).toHaveLength(1);
});
it('keeps a valid sketch after an invalid load and ignores drag frames outside an active gesture', () => {
  const valid = drawingReducer(initialDrawingState, {
    type: 'load',
    shape: 'rectangle',
    anchors: [
      [0, 0],
      [1, 1],
    ],
  });
  const rejected = drawingReducer(valid, {
    type: 'load',
    shape: 'rectangle',
    anchors: [
      [0, 0],
      [1, 1],
      [2, 2],
    ],
  });
  expect(rejected.anchors).toEqual(valid.anchors);
  expect(rejected.error).toMatch(/Too many/);
  const drag = {
    type: 'drag' as const,
    phase: 'move' as const,
    start: [0, 0] as [number, number],
    current: [2, 2] as [number, number],
    tolerance: 0.1,
  };
  expect(drawingReducer(valid, drag)).toBe(valid);
  const pending = { ...valid, interaction: 'drag' as const, picking: true };
  expect(drawingReducer(pending, drag)).toBe(pending);
  expect(
    drawingReducer(valid, {
      type: 'load',
      shape: 'circle',
      anchors: [
        [0, 0],
        [30, 0],
      ],
    }).anchors,
  ).toEqual(valid.anchors);
});
