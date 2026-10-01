import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import * as direction from '@/lib/api/direction';
import { ApiError } from '@/lib/api/errors';
import * as api from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { useOpsPlaylistEditor } from './useOpsPlaylistEditor';

const document: MapWorkspaceDocument = {
  id: 'playlist',
  title: 'Baltic watch',
  kind: 'ops_playlist',
  payload: {},
  revision: 2,
  created_by: plainUser.id,
  team_id: null,
  created_at: '2026-09-30T00:00:00Z',
  updated_at: '2026-09-30T00:00:00Z',
};
const opened: Awaited<ReturnType<typeof api.getPlaylist>> = {
  document,
  playlist: {
    version: 1,
    entries: [{ kind: 'view', id: 'view', caption: 'Watch', dwell_seconds: 60 }],
  },
};
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
  vi.spyOn(api, 'listPlaylists').mockResolvedValue([document]);
  vi.spyOn(api, 'listLiveViews').mockResolvedValue([]);
  vi.spyOn(direction, 'fetchAois').mockResolvedValue([]);
  vi.spyOn(api, 'getPlaylist').mockResolvedValue(opened);
  vi.spyOn(api, 'savePlaylist').mockResolvedValue(document);
  vi.spyOn(api, 'removeLiveDocument').mockResolvedValue(undefined);
});

async function ready() {
  const hook = renderHook(useOpsPlaylistEditor);
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  return hook;
}

it.each(['resolve', 'reject'] as const)(
  'ignores an older open that will %s while a replacement open remains pending',
  async (outcome) => {
    const { result } = await ready();
    const older = deferred<typeof opened>();
    const newer = deferred<typeof opened>();
    vi.mocked(api.getPlaylist)
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(newer.promise);
    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => {
      first = result.current.open('older');
    });
    const oldSignal = vi.mocked(api.getPlaylist).mock.calls[0]?.[1];
    act(() => {
      second = result.current.open('newer');
    });
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => {
      if (outcome === 'resolve') older.resolve(opened);
      else older.reject(new ApiError(409, 'conflict', 'Old access changed'));
      await first;
    });
    expect(result.current).toMatchObject({ active: null, busy: true, error: null, notice: null });
    await act(async () => {
      newer.resolve({ ...opened, document: { ...document, id: 'newer', title: 'New watch' } });
      await second;
    });
    expect(result.current.active?.id).toBe('newer');
    expect(result.current.title).toBe('New watch');
    expect(result.current.entries).toEqual(opened.playlist.entries);
    expect(result.current.busy).toBe(false);
  },
);

it.each(['open', 'save', 'destroy'] as const)(
  'does not resurrect a playlist after access changes during %s',
  async (operation) => {
    const { result } = await ready();
    await act(() => result.current.open(document.id));
    const read = deferred<typeof opened>();
    const write = deferred<MapWorkspaceDocument>();
    const deletion = deferred<undefined>();
    vi.mocked(api.getPlaylist).mockReturnValueOnce(read.promise);
    vi.mocked(api.savePlaylist).mockReturnValueOnce(write.promise);
    vi.mocked(api.removeLiveDocument).mockReturnValueOnce(deletion.promise);
    let work!: Promise<void>;
    act(() => {
      work =
        operation === 'open'
          ? result.current.open(document.id)
          : operation === 'save'
            ? result.current.save()
            : result.current.destroy();
    });
    vi.mocked(api.listPlaylists).mockResolvedValue([]);
    act(() => invalidateWorkspaceAccess());
    expect(result.current).toMatchObject({
      active: null,
      title: 'Wall rotation',
      entries: [],
      busy: false,
      error: null,
      notice: null,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      read.resolve(opened);
      write.resolve(document);
      deletion.resolve(undefined);
      await work;
    });
    expect(result.current.playlists).toEqual([]);
    expect(result.current).toMatchObject({
      active: null,
      title: 'Wall rotation',
      entries: [],
      busy: false,
      error: null,
      notice: null,
    });
  },
);

it('abandons an in-flight open when starting a fresh draft', async () => {
  const { result } = await ready();
  const pending = deferred<typeof opened>();
  vi.mocked(api.getPlaylist).mockReturnValueOnce(pending.promise);
  let work!: Promise<void>;
  act(() => {
    work = result.current.open(document.id);
  });
  const signal = vi.mocked(api.getPlaylist).mock.calls[0]?.[1];
  act(() => {
    result.current.startNew();
    result.current.setTitle('My new draft');
  });
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    pending.resolve(opened);
    await work;
  });
  expect(result.current).toMatchObject({
    active: null,
    title: 'My new draft',
    entries: [],
    busy: false,
    error: null,
    notice: null,
  });
});
