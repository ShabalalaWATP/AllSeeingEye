/** KAN-208: typed dwell times and the delete confirmation in the ops-room playlist panel. */
import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import * as direction from '@/lib/api/direction';
import * as api from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';

import { OpsPlaylistPanel } from './OpsPlaylistPanel';
import { useOpsPlaylistEditor, type OpsPlaylistEditor } from './useOpsPlaylistEditor';

const stamp = '2026-09-30T00:00:00Z';
const document = (id: string, title: string): MapWorkspaceDocument => ({
  id,
  title,
  kind: 'ops_playlist',
  payload: {},
  revision: 1,
  created_by: plainUser.id,
  team_id: null,
  created_at: stamp,
  updated_at: stamp,
});
const view = { ...document('view-1', 'Baltic'), kind: 'live_view' as const };

beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.spyOn(api, 'listPlaylists').mockResolvedValue([]);
  vi.spyOn(api, 'listLiveViews').mockResolvedValue([view]);
  vi.spyOn(direction, 'fetchAois').mockResolvedValue([]);
  vi.spyOn(api, 'savePlaylist').mockResolvedValue(document('saved', 'Wall rotation'));
});

async function editorWithEntry() {
  const hook = renderHook(useOpsPlaylistEditor);
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  const source = hook.result.current.sources[0];
  if (!source) throw new Error('Missing source fixture');
  act(() => hook.result.current.add(source));
  return hook;
}

it('keeps typed dwell text until it is committed, and blank text keeps the last value', async () => {
  const { result } = await editorWithEntry();
  act(() => result.current.typeDwell(0, ''));
  expect(result.current.entries[0]).toMatchObject({ dwell_text: '', dwell_seconds: 60 });
  act(() => result.current.commitDwell(0));
  expect(result.current.entries[0]).toEqual({
    kind: 'view',
    id: view.id,
    caption: '',
    dwell_seconds: 60,
  });
  act(() => result.current.typeDwell(0, '1'));
  act(() => result.current.typeDwell(0, '12'));
  expect(result.current.entries[0]?.dwell_text).toBe('12');
  act(() => result.current.commitDwell(0));
  expect(result.current.entries[0]).toMatchObject({ dwell_seconds: 12 });
  expect(result.current.entries[0]).not.toHaveProperty('dwell_text');
  act(() => result.current.typeDwell(0, '99999'));
  act(() => result.current.update(0, { dwell_seconds: 30 }));
  expect(result.current.entries[0]).toEqual(expect.objectContaining({ dwell_seconds: 30 }));
  expect(result.current.entries[0]).not.toHaveProperty('dwell_text');
});

it('clamps uncommitted dwell text when saving', async () => {
  const { result } = await editorWithEntry();
  act(() => result.current.typeDwell(0, '7200'));
  await act(() => result.current.save());
  expect(api.savePlaylist).toHaveBeenLastCalledWith(
    { version: 1, entries: [{ kind: 'view', id: view.id, caption: '', dwell_seconds: 3600 }] },
    'Wall rotation',
    { existing: null },
    expect.any(AbortSignal),
  );
  expect(result.current.entries[0]).not.toHaveProperty('dwell_text');
});

it('lets the seconds field be cleared and retyped, clamping only on blur', async () => {
  function Harness() {
    return <OpsPlaylistPanel editor={useOpsPlaylistEditor()} onPlay={vi.fn()} />;
  }
  render(<Harness />);
  const picker = await screen.findByLabelText('Add a saved view or area');
  await screen.findByRole('option', { name: 'View: Baltic' });
  fireEvent.change(picker, { target: { value: view.id } });
  fireEvent.click(screen.getByRole('button', { name: 'Add to playlist' }));
  const seconds = screen.getByLabelText('Seconds for entry 1');
  fireEvent.change(seconds, { target: { value: '' } });
  expect(seconds).toHaveValue(null);
  fireEvent.change(seconds, { target: { value: '2' } });
  expect(seconds).toHaveValue(2);
  fireEvent.change(seconds, { target: { value: '25' } });
  expect(seconds).toHaveValue(25);
  fireEvent.blur(seconds);
  expect(seconds).toHaveValue(25);
  fireEvent.change(seconds, { target: { value: '3' } });
  fireEvent.blur(seconds);
  expect(seconds).toHaveValue(5);
});

function fakeEditor(active: MapWorkspaceDocument | null, destroy = vi.fn()) {
  return {
    loading: false,
    loadError: null,
    playlists: [document('a', 'Alpha'), document('b', 'Bravo')],
    sources: [],
    compatible: () => [],
    active,
    title: active?.title ?? '',
    setTitle: vi.fn(),
    entries: [],
    busy: false,
    error: null,
    notice: null,
    reload: vi.fn(),
    startNew: vi.fn(),
    open: vi.fn(),
    add: vi.fn(),
    update: vi.fn(),
    typeDwell: vi.fn(),
    commitDwell: vi.fn(),
    move: vi.fn(),
    remove: vi.fn(),
    save: vi.fn(),
    destroy,
  } satisfies OpsPlaylistEditor;
}

it('drops an open delete confirmation when another playlist is selected', async () => {
  const destroy = vi.fn();
  const alpha = document('a', 'Alpha');
  const page = render(<OpsPlaylistPanel editor={fakeEditor(alpha, destroy)} onPlay={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist' }));
  expect(screen.getByRole('button', { name: 'Confirm delete Alpha' })).toBeInTheDocument();
  page.rerender(
    <OpsPlaylistPanel editor={fakeEditor(document('b', 'Bravo'), destroy)} onPlay={vi.fn()} />,
  );
  expect(screen.queryByRole('button', { name: /Confirm delete/ })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Delete playlist' })).toBeInTheDocument();
  page.rerender(<OpsPlaylistPanel editor={fakeEditor(null, destroy)} onPlay={vi.fn()} />);
  page.rerender(<OpsPlaylistPanel editor={fakeEditor(alpha, destroy)} onPlay={vi.fn()} />);
  expect(screen.queryByRole('button', { name: /Confirm delete/ })).not.toBeInTheDocument();
  expect(destroy).not.toHaveBeenCalled();
});

it('cancels a delete confirmation without deleting', async () => {
  const destroy = vi.fn();
  render(
    <OpsPlaylistPanel editor={fakeEditor(document('a', 'Alpha'), destroy)} onPlay={vi.fn()} />,
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist' }));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.queryByRole('button', { name: /Confirm delete/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Delete playlist' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm delete Alpha' }));
  expect(destroy).toHaveBeenCalledOnce();
});
