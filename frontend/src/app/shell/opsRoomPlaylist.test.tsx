import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { useLiveViewStore } from '@/stores/liveView';
import { server } from '@/test/server';
import { renderApp } from '@/test/render';

const PLAYLIST = '30000000-0000-4000-8000-000000000001';
const AREA = '30000000-0000-4000-8000-000000000002';

afterEach(() => {
  useLiveViewStore.setState({ request: null, playlistId: null, rotationNotice: null });
  useGlobeStore.setState({ opsRoom: false });
});

it('rotates a playlist with alerts still showing, and Escape still exits and stops it', async () => {
  server.use(
    http.get('/api/map/workspaces/:id', () =>
      HttpResponse.json({
        id: PLAYLIST,
        kind: 'ops_playlist',
        title: 'Wall',
        payload: {
          version: 1,
          entries: [{ kind: 'area', id: AREA, caption: 'Watched area', dwell_seconds: 30 }],
        },
        revision: 1,
        created_by: '11111111-1111-4111-8111-111111111111',
        team_id: null,
        created_at: '2026-09-30T00:00:00Z',
        updated_at: '2026-09-30T00:00:00Z',
      }),
    ),
    http.get('/api/direction/aois', () =>
      HttpResponse.json({
        items: [
          {
            id: AREA,
            team_id: null,
            name: 'Area',
            description: '',
            kind: 'bbox',
            bbox: [19, 54, 23, 56],
            countries: [],
            created_by: '11111111-1111-4111-8111-111111111111',
            created_at: '2026-09-30T00:00:00Z',
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/', 'user');
  expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
  act(() => {
    useLiveViewStore.getState().startPlaylist(PLAYLIST);
    useGlobeStore.getState().setOpsRoom(true);
  });
  const rotation = await screen.findByRole('region', { name: 'Ops room rotation' });
  expect(await within(rotation).findByText('Watched area')).toBeInTheDocument();
  const strip = await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
  expect(within(strip).getByText('Kharkiv strikes: 3 items in the last 6 h')).toBeInTheDocument();
  await user.keyboard('{Escape}');
  await waitFor(() => expect(useGlobeStore.getState().opsRoom).toBe(false));
  expect(useLiveViewStore.getState().playlistId).toBeNull();
  expect(screen.queryByRole('region', { name: 'Ops room rotation' })).not.toBeInTheDocument();
});
