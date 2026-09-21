import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useMapDrawing } from './useMapDrawing';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { createMapWorkspaceDocument, getMapWorkspaceDocument } from '@/lib/api/mapWorkspace';

vi.mock('@/lib/api/mapWorkspace', () => ({
  createMapWorkspaceDocument: vi.fn(),
  getMapWorkspaceDocument: vi.fn(),
  listMapWorkspaceDocuments: vi.fn(),
  updateMapWorkspaceDocument: vi.fn(),
}));
const document = {
  id: 'saved',
  kind: 'drawings' as const,
  title: 'Another collection',
  payload: { version: 1, objects: [], selectedId: null },
  revision: 1,
  created_by: 'user',
  team_id: null,
  created_at: '',
  updated_at: '',
};
const engine = { onClick: () => () => undefined };
beforeEach(() => vi.resetAllMocks());
function setup() {
  return renderHook(() => {
    const drawing = useMapDrawing(engine, true);
    return { drawing, workspace: useDrawingWorkspace(drawing, true) };
  });
}
it('requires a decision before replacing unsaved collection and sketch, and cancel preserves undo', async () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([2, 48]));
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  await act(() => result.current.workspace.storage.load('saved'));
  expect(getMapWorkspaceDocument).not.toHaveBeenCalled();
  expect(result.current.workspace.storage.pendingLoad).toBe('saved');
  act(() => result.current.workspace.storage.cancelLoad());
  expect(result.current.workspace.objects).toHaveLength(1);
  expect(result.current.drawing.anchors).toHaveLength(2);
  expect(result.current.workspace.canUndo).toBe(true);
  expect(result.current.drawing.canUndo).toBe(true);
  await act(() => result.current.workspace.storage.load('saved'));
  vi.mocked(getMapWorkspaceDocument).mockResolvedValue(document);
  await act(() => result.current.workspace.storage.confirmLoad('discard'));
  expect(result.current.workspace.objects).toEqual([]);
  expect(result.current.drawing.anchors).toEqual([]);
});
it('rejects a late load when a sketch changes, even while pending edits remains true', async () => {
  const { result } = setup();
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  await act(() => result.current.workspace.storage.load('saved'));
  let finish!: (value: typeof document) => void;
  vi.mocked(getMapWorkspaceDocument).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  let request!: Promise<void>;
  act(() => {
    request = result.current.workspace.storage.confirmLoad('discard');
  });
  act(() =>
    result.current.drawing.load('path', [
      [2, 2],
      [3, 3],
    ]),
  );
  await act(async () => {
    finish(document);
    await request;
  });
  expect(result.current.drawing.anchors).toEqual([
    [2, 2],
    [3, 3],
  ]);
  expect(result.current.workspace.storage.error).toMatch(/changed while/i);
});
it('saves before opening, but does not discard edits made during that save', async () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([2, 48]));
  await act(() => result.current.workspace.storage.load('saved'));
  let finish!: (value: typeof document) => void;
  vi.mocked(createMapWorkspaceDocument).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  let request!: Promise<void>;
  act(() => {
    request = result.current.workspace.storage.confirmLoad('save');
  });
  act(() => result.current.workspace.addPoint([3, 49]));
  await act(async () => {
    finish(document);
    await request;
  });
  expect(getMapWorkspaceDocument).not.toHaveBeenCalled();
  expect(result.current.workspace.objects).toHaveLength(2);
  expect(result.current.workspace.storage.dirty).toBe(true);
});
it('saves the current collection in its chosen workspace before replacing it', async () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([2, 48]));
  await act(() => result.current.workspace.storage.load('saved'));
  vi.mocked(createMapWorkspaceDocument).mockResolvedValue({ ...document, id: 'new' });
  vi.mocked(getMapWorkspaceDocument).mockResolvedValue(document);
  await act(() => result.current.workspace.storage.confirmLoad('save', 'team-id'));
  expect(createMapWorkspaceDocument).toHaveBeenCalledWith(
    expect.objectContaining({
      team_id: 'team-id',
      payload: expect.objectContaining({
        objects: expect.arrayContaining([expect.objectContaining({ anchors: [[2, 48]] })]),
      }),
    }),
    expect.any(AbortSignal),
  );
  expect(result.current.workspace.storage.active?.id).toBe('saved');
  expect(result.current.workspace.storage.pendingLoad).toBeNull();
  expect(result.current.workspace.storage.dirty).toBe(false);
});
it('keeps work and the decision prompt when saving fails or a sketch is still unapplied', async () => {
  const { result } = setup();
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  await act(() => result.current.workspace.storage.load('saved'));
  await act(() => result.current.workspace.storage.confirmLoad('save'));
  expect(createMapWorkspaceDocument).not.toHaveBeenCalled();
  expect(result.current.workspace.storage.error).toMatch(/apply/);
  act(() => result.current.workspace.addSketch());
  vi.mocked(createMapWorkspaceDocument).mockRejectedValue(new Error('network'));
  await act(() => result.current.workspace.storage.confirmLoad('save'));
  expect(getMapWorkspaceDocument).not.toHaveBeenCalled();
  expect(result.current.workspace.objects).toHaveLength(1);
  expect(result.current.workspace.storage.pendingLoad).toBe('saved');
});
it('protects collection edits during an initially clean load', async () => {
  const { result } = setup();
  let finish!: (value: typeof document) => void;
  vi.mocked(getMapWorkspaceDocument).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  let request!: Promise<void>;
  act(() => {
    request = result.current.workspace.storage.load('saved');
  });
  act(() => result.current.workspace.addPoint([2, 48]));
  await act(async () => {
    finish(document);
    await request;
  });
  expect(result.current.workspace.objects).toHaveLength(1);
  expect(result.current.workspace.storage.active).toBeNull();
  expect(result.current.workspace.storage.error).toMatch(/changed while/);
});
