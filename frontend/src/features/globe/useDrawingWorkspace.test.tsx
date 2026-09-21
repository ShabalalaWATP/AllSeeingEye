import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useMapDrawing } from './useMapDrawing';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import {
  createMapWorkspaceDocument,
  getMapWorkspaceDocument,
  listMapWorkspaceDocuments,
} from '@/lib/api/mapWorkspace';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';

vi.mock('@/lib/api/mapWorkspace', () => ({
  createMapWorkspaceDocument: vi.fn(),
  getMapWorkspaceDocument: vi.fn(),
  listMapWorkspaceDocuments: vi.fn(),
  updateMapWorkspaceDocument: vi.fn(),
}));
const engine = { onClick: () => () => undefined };
beforeEach(() => vi.clearAllMocks());
function setup() {
  return renderHook(() => {
    const drawing = useMapDrawing(engine, true);
    return { drawing, workspace: useDrawingWorkspace(drawing, true) };
  });
}
it('edits selected geometry, protects locked drawings and undoes complete collection operations', () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([-2, 54]));
  const id = result.current.workspace.objects[0]?.id ?? '';
  act(() =>
    result.current.workspace.updateObject(id, {
      name: 'Observation',
      anchors: [[-3, 55]],
      locked: true,
    }),
  );
  expect(result.current.workspace.selected?.anchors).toEqual([[-3, 55]]);
  act(() => result.current.workspace.remove(id));
  expect(result.current.workspace.error).toMatch(/Unlock/);
  expect(result.current.workspace.objects).toHaveLength(1);
  act(() => result.current.workspace.undo());
  expect(result.current.workspace.selected?.name).toBe('Point 1');
  act(() => result.current.workspace.redo());
  expect(result.current.workspace.selected?.name).toBe('Observation');
  act(() => result.current.workspace.duplicate(id));
  expect(result.current.workspace.objects).toHaveLength(2);
  expect(result.current.workspace.selected?.locked).toBe(false);
  act(() => invalidateWorkspaceAccess());
  expect(result.current.workspace.objects).toHaveLength(0);
  expect(result.current.workspace.canUndo).toBe(false);
});
it('saves collection payload and never applies an old read after authority invalidation', async () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([0, 0]));
  const document = {
    id: 'saved',
    kind: 'drawings' as const,
    title: 'Map drawings',
    payload: {
      version: 1,
      objects: result.current.workspace.objects,
      selectedId: result.current.workspace.selectedId,
    },
    revision: 1,
    created_by: 'user',
    team_id: null,
    created_at: '',
    updated_at: '',
  };
  vi.mocked(createMapWorkspaceDocument).mockResolvedValue(document);
  await act(() => result.current.workspace.storage.save());
  expect(createMapWorkspaceDocument).toHaveBeenCalledWith(
    expect.objectContaining({
      kind: 'drawings',
      payload: expect.objectContaining({ objects: expect.any(Array) }),
    }),
    expect.any(AbortSignal),
  );
  let resolve!: (value: typeof document) => void;
  vi.mocked(getMapWorkspaceDocument).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  let request!: Promise<void>;
  act(() => {
    request = result.current.workspace.storage.load('saved');
  });
  act(() => invalidateWorkspaceAccess());
  await act(async () => {
    resolve(document);
    await request;
  });
  expect(result.current.workspace.objects).toEqual([]);
  expect(result.current.workspace.storage.active).toBeNull();
});
it('starts a fresh undo history when opening a saved collection', async () => {
  const { result } = setup();
  act(() => result.current.workspace.addPoint([0, 0]));
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  vi.mocked(getMapWorkspaceDocument).mockResolvedValue({
    id: 'saved',
    kind: 'drawings',
    title: 'Different collection',
    payload: { version: 1, objects: [], selectedId: null },
    revision: 1,
    created_by: 'user',
    team_id: null,
    created_at: '',
    updated_at: '',
  });
  await act(() => result.current.workspace.storage.load('saved'));
  await act(() => result.current.workspace.storage.confirmLoad('discard'));
  expect(result.current.workspace.objects).toEqual([]);
  expect(result.current.workspace.canUndo).toBe(false);
  expect(result.current.drawing.canUndo).toBe(false);
});
it('hides a selected shape and clears its editor overlay; blocks saving unapplied geometry', async () => {
  const { result } = setup();
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [1, 1],
    ]),
  );
  await act(() => result.current.workspace.storage.save());
  expect(createMapWorkspaceDocument).not.toHaveBeenCalled();
  expect(result.current.workspace.storage.error).toMatch(/sketch/);
  act(() => result.current.workspace.addSketch());
  const id = result.current.workspace.selectedId;
  act(() => result.current.workspace.select(id));
  expect(result.current.workspace.storage.pendingEdits).toBe(false);
  act(() =>
    result.current.drawing.load('path', [
      [2, 2],
      [3, 3],
    ]),
  );
  expect(result.current.workspace.storage.pendingEdits).toBe(true);
  act(() => result.current.workspace.applySketch());
  expect(result.current.workspace.storage.pendingEdits).toBe(false);
  act(() => result.current.workspace.updateObject(String(id), { visible: false }));
  expect(result.current.drawing.anchors).toEqual([]);
  expect(result.current.workspace.layers).toEqual([]);
});
it.each(['role', 'is_active', 'status'] as const)(
  'clears geometry, history and late reads on same-user %s changes without SSE',
  async (field) => {
    useAuthStore.getState().setSession(tokenFor({ ...plainUser, role: 'admin' }));
    const { result } = setup();
    act(() => result.current.workspace.addPoint([0, 0]));
    act(() =>
      result.current.drawing.load('path', [
        [0, 0],
        [1, 1],
      ]),
    );
    const document = {
      id: 'saved',
      kind: 'drawings' as const,
      title: 'Map drawings',
      payload: {
        version: 1,
        objects: result.current.workspace.objects,
        selectedId: result.current.workspace.selectedId,
      },
      revision: 1,
      created_by: 'user',
      team_id: null,
      created_at: '',
      updated_at: '',
    };
    let resolve!: (value: (typeof document)[]) => void;
    vi.mocked(listMapWorkspaceDocuments).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    let request!: Promise<void>;
    act(() => {
      request = result.current.workspace.storage.browse();
    });
    act(() => {
      if (field === 'status') useAuthStore.setState({ status: 'anonymous' });
      else
        useAuthStore.getState().setSession(
          tokenFor({
            ...plainUser,
            role: field === 'role' ? 'user' : 'admin',
            is_active: field !== 'is_active',
          }),
        );
    });
    await act(async () => {
      resolve([document]);
      await request;
    });
    expect(result.current.workspace.storage.documents).toEqual([]);
    expect(result.current.workspace.objects).toEqual([]);
    expect(result.current.workspace.canUndo).toBe(false);
    expect(result.current.drawing.canUndo).toBe(false);
    expect(result.current.drawing.anchors).toEqual([]);
  },
);
it('loads older collection pages explicitly, deduplicates IDs and resets paging on browse', async () => {
  const { result } = setup();
  const document = {
    id: 'saved',
    kind: 'drawings' as const,
    title: 'Map drawings',
    payload: { version: 1, objects: [], selectedId: null },
    revision: 1,
    created_by: 'user',
    team_id: null,
    created_at: '',
    updated_at: '',
  };
  vi.mocked(listMapWorkspaceDocuments)
    .mockResolvedValueOnce(
      Array.from({ length: 100 }, (_, index) => ({ ...document, id: String(index) })),
    )
    .mockResolvedValueOnce([
      { ...document, id: '99' },
      { ...document, id: '100' },
    ])
    .mockResolvedValueOnce([]);
  await act(() => result.current.workspace.storage.browse());
  expect(result.current.workspace.storage.hasMore).toBe(true);
  await act(() => result.current.workspace.storage.loadMore());
  expect(listMapWorkspaceDocuments).toHaveBeenLastCalledWith('drawings', expect.any(AbortSignal), {
    offset: 100,
    limit: 100,
  });
  expect(result.current.workspace.storage.documents).toHaveLength(101);
  expect(result.current.workspace.storage.hasMore).toBe(false);
  await act(() => result.current.workspace.storage.browse());
  expect(listMapWorkspaceDocuments).toHaveBeenLastCalledWith('drawings', expect.any(AbortSignal), {
    offset: 0,
    limit: 100,
  });
  expect(result.current.workspace.storage.documents).toEqual([]);
});
it('discards a late saved collection load after a same-user role downgrade', async () => {
  useAuthStore.getState().setSession(tokenFor({ ...plainUser, role: 'admin' }));
  const { result } = setup();
  const document = {
    id: 'saved',
    kind: 'drawings' as const,
    title: 'Private drawing',
    payload: { version: 1, objects: [], selectedId: null },
    revision: 1,
    created_by: 'user',
    team_id: null,
    created_at: '',
    updated_at: '',
  };
  let finish: () => void = () => undefined;
  vi.mocked(getMapWorkspaceDocument).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = () => resolve(document);
      }),
  );
  let request = Promise.resolve();
  act(() => {
    request = result.current.workspace.storage.load('saved');
  });
  act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
  await act(async () => {
    finish();
    await request;
  });
  expect(result.current.workspace.storage.active).toBeNull();
  expect(result.current.workspace.storage.notice).toBeNull();
});
