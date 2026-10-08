import { fireEvent, render, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { server } from '@/test/server';
import { OpsPlaylistPanel } from './OpsPlaylistPanel';
import { useOpsPlaylistEditor } from './useOpsPlaylistEditor';

const VIEW = '20000000-0000-4000-8000-000000000001';
const TEAM_VIEW = '20000000-0000-4000-8000-000000000002';
const AREA = '20000000-0000-4000-8000-000000000003';
const TEAM = '20000000-0000-4000-8000-000000000009';
const stamp = '2026-09-30T00:00:00Z';
const view = (id: string, title: string, team_id: string | null) => ({
  id,
  kind: 'live_view',
  title,
  payload: {},
  revision: 1,
  created_by: plainUser.id,
  team_id,
  created_at: stamp,
  updated_at: stamp,
});
let saved: { kind: string; title: string; payload: { entries: object[] } } | null;

function Harness({ onPlay }: { onPlay: (id: string) => void }) {
  const editor = useOpsPlaylistEditor();
  return <OpsPlaylistPanel editor={editor} onPlay={onPlay} />;
}

beforeEach(() => {
  saved = null;
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  server.use(
    http.get('/api/map/workspaces', ({ request }) => {
      const kind = new URL(request.url).searchParams.get('kind');
      return HttpResponse.json(
        kind === 'live_view' ? [view(VIEW, 'Baltic', null), view(TEAM_VIEW, 'Team', TEAM)] : [],
      );
    }),
    http.get('/api/direction/aois', () =>
      HttpResponse.json({
        items: [
          {
            id: AREA,
            team_id: null,
            name: 'Kaliningrad',
            description: '',
            kind: 'bbox',
            bbox: [19, 54, 23, 56],
            countries: [],
            created_by: plainUser.id,
            created_at: stamp,
          },
        ],
      }),
    ),
    http.post('/api/map/workspaces', async ({ request }) => {
      saved = (await request.json()) as typeof saved;
      return HttpResponse.json(
        {
          ...view('20000000-0000-4000-8000-000000000010', 'Wall rotation', null),
          kind: 'ops_playlist',
          payload: saved?.payload,
        },
        { status: 201 },
      );
    }),
  );
});

it('builds a playlist from same-scope views and areas, bounds dwell time and plays it', async () => {
  const onPlay = vi.fn();
  render(<Harness onPlay={onPlay} />);
  const picker = await screen.findByLabelText('Add a saved view or area');
  await screen.findByRole('option', { name: 'View: Baltic' });
  expect(within(picker).queryByRole('option', { name: 'View: Team' })).not.toBeInTheDocument();
  fireEvent.change(picker, { target: { value: VIEW } });
  fireEvent.click(screen.getByRole('button', { name: 'Add to playlist' }));
  fireEvent.change(picker, { target: { value: AREA } });
  fireEvent.click(screen.getByRole('button', { name: 'Add to playlist' }));
  fireEvent.change(screen.getByLabelText('Caption for entry 1'), {
    target: { value: 'Baltic aviation' },
  });
  fireEvent.change(screen.getByLabelText('Seconds for entry 2'), { target: { value: '1' } });
  expect(screen.getByLabelText('Seconds for entry 2')).toHaveValue(1);
  fireEvent.blur(screen.getByLabelText('Seconds for entry 2'));
  expect(screen.getByLabelText('Seconds for entry 2')).toHaveValue(5);
  fireEvent.click(screen.getByRole('button', { name: 'Move entry 2 earlier' }));
  expect(screen.getByText('1. Area: Kaliningrad')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save playlist' }));
  await screen.findByText('Saved Wall rotation (revision 1).');
  expect(saved).toMatchObject({
    kind: 'ops_playlist',
    payload: {
      version: 1,
      entries: [
        { kind: 'area', id: AREA, caption: '', dwell_seconds: 5 },
        { kind: 'view', id: VIEW, caption: 'Baltic aviation', dwell_seconds: 60 },
      ],
    },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Play saved playlist in ops room' }));
  expect(onPlay).toHaveBeenCalledWith('20000000-0000-4000-8000-000000000010');
});
