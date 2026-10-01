import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as api from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { useLiveViewLibrary } from './useLiveViewLibrary';

const view: LiveViewState = {
  version: 1,
  projection: 'map',
  camera: { center: [24, 57], zoom: 5, bearing: 0, pitch: 0 },
  base_layer: 'dark',
  layers: ['aviation'],
  window_hours: 24,
  nation: 'EE',
  filters: { flight: 'military' },
  plan_id: null,
};
const document = (id: string, title = id): MapWorkspaceDocument => ({
  id,
  title,
  kind: 'live_view',
  payload: {},
  revision: 3,
  created_by: plainUser.id,
  team_id: null,
  created_at: '2026-09-30T00:00:00Z',
  updated_at: '2026-09-30T00:00:00Z',
});
const original = document('original', 'Baltic');
const other = document('other', 'North Sea');

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.spyOn(api, 'listLiveViews').mockResolvedValue([other, original]);
  vi.spyOn(api, 'saveLiveView').mockResolvedValue(original);
  vi.spyOn(api, 'removeLiveDocument').mockResolvedValue(undefined);
});

async function ready() {
  const hook = renderHook(useLiveViewLibrary);
  await waitFor(() => expect(hook.result.current.busy).toBe(false));
  return hook;
}

it('updates the selected revision once at the front and deletes only that saved view', async () => {
  const { result } = await ready();
  act(() => result.current.select(original));
  const revised = { ...original, title: 'Updated Baltic', revision: 4 };
  vi.mocked(api.saveLiveView).mockResolvedValueOnce(revised);
  await act(() => result.current.save(view, '  Updated Baltic  ', true));
  expect(api.saveLiveView).toHaveBeenCalledWith(
    view,
    'Updated Baltic',
    { existing: original },
    expect.any(AbortSignal),
  );
  expect(result.current.items).toEqual([revised, other]);
  expect(result.current.active).toEqual(revised);
  expect(result.current.notice).toBe('Saved Updated Baltic (revision 4).');
  await act(() => result.current.remove(revised));
  expect(api.removeLiveDocument).toHaveBeenCalledWith(revised.id, expect.any(AbortSignal));
  expect(result.current.items).toEqual([other]);
  expect(result.current.active).toBeNull();
  expect(result.current.notice).toBe('Deleted Updated Baltic.');
});

it('creates in the chosen team without overwriting the selected personal view', async () => {
  const { result } = await ready();
  act(() => result.current.select(original));
  const shared = { ...document('shared', 'Team picture'), team_id: 'team-1' };
  vi.mocked(api.saveLiveView).mockResolvedValueOnce(shared);
  await act(() => result.current.save(view, ' Team picture ', false, 'team-1'));
  expect(api.saveLiveView).toHaveBeenCalledWith(
    view,
    'Team picture',
    { existing: null, teamId: 'team-1' },
    expect.any(AbortSignal),
  );
  expect(result.current.items).toEqual([shared, other, original]);
  act(() => result.current.select(null));
  expect(result.current.active).toBeNull();
});

it.each([
  [new ApiError(409, 'conflict', 'Revision conflict'), 'changed elsewhere'],
  [new ApiError(503, 'unavailable', 'Storage unavailable'), 'Storage unavailable'],
  [new Error('private diagnostic'), 'Something went wrong. Please try again.'],
])(
  'keeps a view on failed deletion and clears the error after a successful retry: %s',
  async (error, message) => {
    const { result } = await ready();
    act(() => result.current.select(original));
    vi.mocked(api.removeLiveDocument).mockRejectedValueOnce(error);
    await act(() => result.current.remove(original));
    expect(result.current.error).toContain(message);
    expect(result.current.active).toEqual(original);
    expect(result.current.items).toContainEqual(original);
    expect(result.current.busy).toBe(false);
    await act(() => result.current.remove(original));
    expect(result.current.error).toBeNull();
    expect(result.current.items).not.toContainEqual(original);
  },
);

it('refreshes a failed listing without retaining its error or selection', async () => {
  vi.mocked(api.listLiveViews).mockRejectedValueOnce(new ApiError(503, 'offline', 'List offline'));
  const { result } = await ready();
  expect(result.current.items).toEqual([]);
  expect(result.current.error).toBe('List offline');
  act(() => result.current.refresh());
  await waitFor(() => expect(result.current.items).toEqual([other, original]));
  expect(result.current.error).toBeNull();
  expect(result.current.active).toBeNull();
});

it('retains a successful new save when the list was unavailable, then refreshes the catalogue', async () => {
  vi.mocked(api.listLiveViews).mockRejectedValueOnce(new ApiError(503, 'offline', 'List offline'));
  const { result } = await ready();
  const saved = document('new', 'New picture');
  vi.mocked(api.saveLiveView).mockResolvedValueOnce(saved);
  await act(() => result.current.save(view, saved.title, false));
  expect(result.current.items).toEqual([saved]);
  expect(result.current.active).toEqual(saved);
  expect(result.current.notice).toBe('Saved New picture (revision 3).');
  expect(result.current.error).toBe('List offline');
  vi.mocked(api.listLiveViews).mockResolvedValueOnce([saved, other, original]);
  act(() => result.current.refresh());
  await waitFor(() => expect(result.current.items).toEqual([saved, other, original]));
  expect(result.current.error).toBeNull();
  expect(result.current.active).toEqual(saved);
});

it.each(['resolve', 'reject'] as const)(
  'keeps the latest save busy and ignores an older save that will %s after cancellation',
  async (outcome) => {
    const { result } = await ready();
    const old = deferred<MapWorkspaceDocument>();
    const latest = deferred<MapWorkspaceDocument>();
    vi.mocked(api.saveLiveView)
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(latest.promise);
    let oldSave!: Promise<void>;
    let latestSave!: Promise<void>;
    act(() => {
      oldSave = result.current.save(view, 'Old', false);
    });
    const oldSignal = vi.mocked(api.saveLiveView).mock.calls[0]?.[3];
    act(() => {
      latestSave = result.current.save(view, 'Latest', false);
    });
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => {
      if (outcome === 'resolve') old.resolve(document('old'));
      else old.reject(new ApiError(409, 'conflict', 'Old conflict'));
      await oldSave;
    });
    expect(result.current.busy).toBe(true);
    expect(result.current.notice).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.items).toEqual([other, original]);
    await act(async () => {
      latest.resolve(document('latest'));
      await latestSave;
    });
    expect(result.current.active?.id).toBe('latest');
    expect(result.current.busy).toBe(false);
  },
);

it.each(['save', 'remove'] as const)(
  'discards a late %s completion after workspace access changes',
  async (operation) => {
    const { result } = await ready();
    act(() => result.current.select(original));
    const pendingSave = deferred<MapWorkspaceDocument>();
    const pendingDelete = deferred<undefined>();
    vi.mocked(api.saveLiveView).mockReturnValueOnce(pendingSave.promise);
    vi.mocked(api.removeLiveDocument).mockReturnValueOnce(pendingDelete.promise);
    let work!: Promise<void>;
    act(() => {
      work =
        operation === 'save'
          ? result.current.save(view, 'Old scope', true)
          : result.current.remove(original);
    });
    vi.mocked(api.listLiveViews).mockResolvedValue([]);
    act(() => invalidateWorkspaceAccess());
    expect(result.current.active).toBeNull();
    await waitFor(() => expect(result.current.busy).toBe(false));
    await act(async () => {
      pendingSave.resolve(document('leaked'));
      pendingDelete.resolve(undefined);
      await work;
    });
    expect(result.current.items).toEqual([]);
    expect(result.current.active).toBeNull();
    expect(result.current.notice).toBeNull();
    expect(result.current.error).toBeNull();
  },
);

it('aborts pending writes when the library unmounts', async () => {
  const { result, unmount } = await ready();
  const pending = deferred<MapWorkspaceDocument>();
  vi.mocked(api.saveLiveView).mockReturnValueOnce(pending.promise);
  let work!: Promise<void>;
  act(() => {
    work = result.current.save(view, 'Closing panel', false);
  });
  const signal = vi.mocked(api.saveLiveView).mock.calls[0]?.[3];
  unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    pending.resolve(original);
    await work;
  });
});
