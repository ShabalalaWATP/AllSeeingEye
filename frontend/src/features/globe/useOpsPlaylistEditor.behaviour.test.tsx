import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import * as direction from '@/lib/api/direction';
import { ApiError } from '@/lib/api/errors';
import * as api from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { MAX_PLAYLIST_ENTRIES, type PlaylistEntry } from '@/lib/liveViews/opsPlaylist';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { useOpsPlaylistEditor } from './useOpsPlaylistEditor';

const document = (id: string, team_id: string | null = null): MapWorkspaceDocument => ({
  id,
  title: id,
  kind: 'live_view',
  payload: {},
  revision: 2,
  created_by: plainUser.id,
  team_id,
  created_at: '2026-09-30T00:00:00Z',
  updated_at: '2026-09-30T00:00:00Z',
});
const personal = document('personal');
const shared = document('shared', 'team-1');
const playlist = { ...document('playlist'), kind: 'ops_playlist' as const };
const entry: PlaylistEntry = { kind: 'view', id: personal.id, caption: 'First', dwell_seconds: 60 };
const area: direction.AreaOfInterest = {
  id: 'area',
  name: 'Baltic coast',
  team_id: null,
  created_by: plainUser.id,
  created_at: '2026-09-30T00:00:00Z',
  kind: 'bbox',
  bbox: [19, 54, 23, 56],
  countries: [],
  description: '',
};

beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.spyOn(api, 'listPlaylists').mockResolvedValue([playlist]);
  vi.spyOn(api, 'listLiveViews').mockResolvedValue([
    personal,
    shared,
    document('another-team', 'team-2'),
    { ...document('another-owner'), created_by: 'other-user' },
  ]);
  vi.spyOn(direction, 'fetchAois').mockResolvedValue([
    area,
    { ...area, id: 'shared-area', team_id: 'team-1', created_by: 'other-user' },
  ]);
  vi.spyOn(api, 'getPlaylist').mockResolvedValue({
    document: playlist,
    playlist: { version: 1, entries: [entry] },
  });
  vi.spyOn(api, 'savePlaylist').mockResolvedValue({ ...playlist, revision: 3 });
  vi.spyOn(api, 'removeLiveDocument').mockResolvedValue(undefined);
});

async function ready() {
  const hook = renderHook(useOpsPlaylistEditor);
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  return hook;
}

it('offers only the current personal owner or matching team for both source kinds', async () => {
  const { result } = await ready();
  expect(result.current.compatible(null).map(({ label }) => label)).toEqual([
    'View: personal',
    'Area: Baltic coast',
  ]);
  expect(result.current.compatible('team-1').map(({ id }) => id)).toEqual([
    'shared',
    'shared-area',
  ]);
  expect(result.current.compatible('missing-team')).toEqual([]);
  act(() => useAuthStore.setState({ user: null, status: 'anonymous' }));
  expect(result.current.compatible(null)).toEqual([]);
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.compatible(null)).toEqual([]);
});

it('bounds additions and dwell times while preserving captions and deliberate ordering', async () => {
  const { result } = await ready();
  const [viewSource, areaSource] = [result.current.sources[0], result.current.sources[4]];
  if (!viewSource || !areaSource) throw new Error('Missing source fixtures');
  act(() => {
    result.current.add(viewSource);
    result.current.add(areaSource);
    result.current.update(0, { caption: 'First view' });
    result.current.update(1, { dwell_seconds: 0 });
  });
  expect(result.current.entries).toEqual([
    { kind: 'view', id: personal.id, caption: 'First view', dwell_seconds: 60 },
    { kind: 'area', id: area.id, caption: '', dwell_seconds: 5 },
  ]);
  act(() => {
    result.current.move(0, -1);
    result.current.move(1, 1);
  });
  expect(result.current.entries.map(({ id }) => id)).toEqual([personal.id, area.id]);
  act(() => result.current.move(0, 1));
  expect(result.current.entries.map(({ id }) => id)).toEqual([area.id, personal.id]);
  act(() => result.current.update(1, { dwell_seconds: 5000 }));
  expect(result.current.entries[1]).toMatchObject({ caption: 'First view', dwell_seconds: 3600 });
  act(() => result.current.remove(0));
  expect(result.current.entries.map(({ id }) => id)).toEqual([personal.id]);
  act(() => {
    for (let index = 0; index < MAX_PLAYLIST_ENTRIES; index += 1) result.current.add(areaSource);
  });
  expect(result.current.entries).toHaveLength(MAX_PLAYLIST_ENTRIES);
  expect(result.current.entries[0]?.caption).toBe('First view');
});

it('saves a new team playlist, then retains its revision when updating and refreshing the list', async () => {
  const { result } = await ready();
  const source = result.current.compatible('team-1')[0];
  if (!source) throw new Error('Missing team source');
  act(() => {
    result.current.setTitle('  Team wall  ');
    result.current.add(source);
  });
  const created = { ...playlist, team_id: 'team-1', title: 'Team wall', revision: 1 };
  vi.mocked(api.savePlaylist).mockResolvedValueOnce(created);
  vi.mocked(api.listPlaylists).mockResolvedValue([created]);
  await act(() => result.current.save('team-1'));
  expect(api.savePlaylist).toHaveBeenLastCalledWith(
    { version: 1, entries: [{ kind: 'view', id: shared.id, caption: '', dwell_seconds: 60 }] },
    'Team wall',
    { existing: null, teamId: 'team-1' },
    expect.any(AbortSignal),
  );
  expect(result.current.active).toEqual(created);
  expect(result.current.notice).toBe('Saved Team wall (revision 1).');
  await waitFor(() => expect(result.current.playlists).toEqual([created]));
  act(() => result.current.setTitle('Revised wall'));
  await act(() => result.current.save());
  expect(api.savePlaylist).toHaveBeenLastCalledWith(
    expect.objectContaining({ version: 1 }),
    'Revised wall',
    { existing: created },
    expect.any(AbortSignal),
  );
  expect(result.current.active?.revision).toBe(3);
});

it('opens saved entries and clears the editor only after successful deletion', async () => {
  const { result } = await ready();
  await act(() => result.current.open(playlist.id));
  expect(result.current.title).toBe(playlist.title);
  expect(result.current.entries).toEqual([entry]);
  vi.mocked(api.removeLiveDocument).mockRejectedValueOnce(
    new ApiError(503, 'offline', 'Storage offline'),
  );
  await act(() => result.current.destroy());
  expect(result.current.error).toBe('Storage offline');
  expect(result.current.active).toEqual(playlist);
  expect(result.current.entries).toEqual([entry]);
  vi.mocked(api.listPlaylists).mockResolvedValue([]);
  await act(() => result.current.destroy());
  expect(api.removeLiveDocument).toHaveBeenLastCalledWith(playlist.id, expect.any(AbortSignal));
  expect(result.current.active).toBeNull();
  expect(result.current.title).toBe('Wall rotation');
  expect(result.current.entries).toEqual([]);
  expect(result.current.notice).toBe('Deleted playlist.');
  expect(result.current.error).toBeNull();
  expect(result.current.busy).toBe(false);
  await waitFor(() => expect(result.current.playlists).toEqual([]));
  await act(() => result.current.destroy());
  expect(api.removeLiveDocument).toHaveBeenCalledTimes(2);
});

it.each([
  [new ApiError(409, 'conflict', 'Revision conflict'), 'changed elsewhere'],
  [new Error('private diagnostic'), 'Something went wrong. Please try again.'],
])(
  'preserves the draft on save failure, then clears the message on retry: %s',
  async (error, message) => {
    const { result } = await ready();
    await act(() => result.current.open(playlist.id));
    act(() => result.current.update(0, { caption: 'Unsaved draft' }));
    vi.mocked(api.savePlaylist).mockRejectedValueOnce(error);
    await act(() => result.current.save());
    expect(result.current.error).toContain(message);
    expect(result.current.entries[0]?.caption).toBe('Unsaved draft');
    expect(result.current.active?.revision).toBe(2);
    expect(result.current.busy).toBe(false);
    await act(() => result.current.save());
    expect(result.current.error).toBeNull();
    expect(result.current.notice).toBe('Saved playlist (revision 3).');
    act(() => result.current.startNew());
    expect(result.current).toMatchObject({ active: null, entries: [], error: null, notice: null });
  },
);

it('shows a failed source load and reloads sources without a stale load error', async () => {
  vi.mocked(direction.fetchAois).mockRejectedValueOnce(
    new ApiError(503, 'offline', 'Areas offline'),
  );
  const { result } = await ready();
  expect(result.current.loadError).toBe('Areas offline');
  expect(result.current.sources).toEqual([]);
  expect(result.current.playlists).toEqual([]);
  expect(result.current.compatible(null)).toEqual([]);
  act(() => result.current.reload());
  await waitFor(() => expect(result.current.sources).toHaveLength(6));
  expect(result.current.loadError).toBeNull();
  expect(result.current.playlists).toEqual([playlist]);
});
