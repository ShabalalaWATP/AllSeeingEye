import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useLiveViewStore } from '@/stores/liveView';
import { plainUser } from '@/test/fixtures';
import { server } from '@/test/server';
import OpsRoomRotation from './OpsRoomRotation';

const PLAYLIST = '10000000-0000-4000-8000-000000000001';
const VIEW = '10000000-0000-4000-8000-000000000002';
const AREA = '10000000-0000-4000-8000-000000000003';
const GONE = '10000000-0000-4000-8000-000000000004';
const camera = { center: [24.5, 57.2], zoom: 4.5, bearing: 0, pitch: 0 };
const viewPayload = {
  version: 1,
  projection: 'globe',
  camera,
  base_layer: 'dark',
  layers: ['aviation'],
  window_hours: 24,
  nation: null,
  filters: {},
  plan_id: null,
};

function doc(id: string, kind: string, title: string, payload: object) {
  return {
    id,
    kind,
    title,
    payload,
    revision: 1,
    created_by: plainUser.id,
    team_id: null,
    created_at: '2026-09-30T00:00:00Z',
    updated_at: '2026-09-30T00:00:00Z',
  };
}
const area = {
  id: AREA,
  team_id: null,
  name: 'Kaliningrad',
  description: '',
  kind: 'bbox',
  bbox: [19, 54, 23, 56],
  countries: [],
  created_by: plainUser.id,
  created_at: '2026-09-30T00:00:00Z',
};
let entries: object[];
let playlistReads = 0;

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: state });
  document.dispatchEvent(new Event('visibilitychange'));
}

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  playlistReads = 0;
  entries = [
    { kind: 'view', id: VIEW, caption: 'Baltic aviation', dwell_seconds: 10 },
    { kind: 'area', id: AREA, caption: '', dwell_seconds: 5 },
    { kind: 'view', id: GONE, caption: 'Deleted view', dwell_seconds: 5 },
  ];
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  useLiveViewStore.setState({ request: null, playlistId: PLAYLIST, rotationNotice: null });
  setVisibility('visible');
  server.use(
    http.get('/api/map/workspaces/:id', ({ params }) => {
      if (params.id === PLAYLIST) {
        playlistReads += 1;
        return HttpResponse.json(doc(PLAYLIST, 'ops_playlist', 'Wall', { version: 1, entries }));
      }
      if (params.id === VIEW)
        return HttpResponse.json(doc(VIEW, 'live_view', 'Baltic', viewPayload));
      return HttpResponse.json({ detail: 'Not found.' }, { status: 404 });
    }),
    http.get('/api/direction/aois', () => HttpResponse.json({ items: [area] })),
  );
});

afterEach(() => {
  vi.useRealTimers();
  useLiveViewStore.setState({ request: null, playlistId: null, rotationNotice: null });
});

describe('ops room rotation', () => {
  it('cycles at each dwell time, focuses areas and skips unavailable entries visibly', async () => {
    render(<OpsRoomRotation />);
    expect(await screen.findByText('Baltic aviation')).toBeInTheDocument();
    expect(screen.getByText('1 of 3')).toBeInTheDocument();
    expect(useLiveViewStore.getState().request).toMatchObject({ kind: 'view' });
    expect(screen.getByTestId('ops-room-announcer')).toHaveTextContent(
      'Showing 1 of 3: Baltic aviation',
    );
    await advance(9_000);
    expect(screen.getByText('Baltic aviation')).toBeInTheDocument();
    await advance(1_000);
    expect(await screen.findByText('Kaliningrad')).toBeInTheDocument();
    expect(useLiveViewStore.getState().request).toMatchObject({ kind: 'area', areaId: AREA });
    await advance(5_000);
    expect(await screen.findByText(/Skipped 3 \(Deleted view\)/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('1 of 3')).toBeInTheDocument());
    expect(playlistReads).toBe(2);
  });

  it('pauses while the tab is hidden and resumes with the remaining time', async () => {
    render(<OpsRoomRotation />);
    await screen.findByText('Baltic aviation');
    await advance(4_000);
    setVisibility('hidden');
    await advance(60_000);
    expect(screen.getByText('Baltic aviation')).toBeInTheDocument();
    setVisibility('visible');
    await advance(5_000);
    expect(screen.getByText('Baltic aviation')).toBeInTheDocument();
    await advance(1_100);
    expect(await screen.findByText('Kaliningrad')).toBeInTheDocument();
  });

  it('pauses on interaction and has accessible controls', async () => {
    render(<OpsRoomRotation />);
    await screen.findByText('Baltic aviation');
    fireEvent.pointerDown(document.body);
    expect(screen.getByText('Paused while you interact')).toBeInTheDocument();
    await advance(20_000);
    expect(screen.getByText('Baltic aviation')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Resume rotation' }));
    await advance(10_000);
    expect(await screen.findByText('Kaliningrad')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Previous view' }));
    expect(await screen.findByText('Baltic aviation')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Pause rotation' }));
    expect(screen.getByRole('button', { name: 'Resume rotation' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Stop rotation' }));
    expect(useLiveViewStore.getState().playlistId).toBeNull();
  });

  it('stops and forgets private state when access changes', async () => {
    render(<OpsRoomRotation />);
    await screen.findByText('Baltic aviation');
    act(() => invalidateWorkspaceAccess());
    expect(useLiveViewStore.getState()).toMatchObject({
      playlistId: null,
      request: null,
      rotationNotice: 'The rotation stopped because your access changed.',
    });
  });

  it('stops with a notice when the playlist itself is unavailable', async () => {
    useLiveViewStore.setState({ playlistId: GONE });
    render(<OpsRoomRotation />);
    await waitFor(() =>
      expect(useLiveViewStore.getState().rotationNotice).toBe(
        'This playlist is unavailable or you no longer have access.',
      ),
    );
    expect(useLiveViewStore.getState().playlistId).toBeNull();
  });
});
