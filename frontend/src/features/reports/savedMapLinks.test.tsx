import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { report, plainUser, adminUser } from '@/test/fixtures';
import { savedMapFixture as saved } from '@/test/fixtures.savedMaps';
import { renderApp, applySession } from '@/test/render';
import { server } from '@/test/server';
import { roster } from '@/test/fixtures.teams';

it('resolves the exact immutable view before requesting its anchored report version without opening tiles', async () => {
  const requests: string[] = [];
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => {
      requests.push('map');
      return HttpResponse.json(saved);
    }),
    http.get('/api/reports/:id', ({ request }) => {
      requests.push(new URL(request.url).search);
      return HttpResponse.json({ ...report, report: { ...report.report, latest_version: 3 } });
    }),
  );
  renderApp(
    `/reports/${report.report.id}?version=1&map_view=view-1&map_revision=revision-1`,
    'user',
  );
  await screen.findByRole('heading', { name: 'Map and timeline' });
  expect(requests.slice(0, 2)).toEqual(['map', '?version=1']);
  expect(screen.getByLabelText('Map view title')).toHaveValue('Saved geography');
  expect(screen.getByRole('button', { name: 'Open evidence map' })).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Saved evidence flat map' })).not.toBeInTheDocument();
});

it('rejects missing or mismatched version anchors without displaying latest report evidence', async () => {
  let reports = 0;
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => HttpResponse.json(saved)),
    http.get('/api/reports/:id', () => {
      reports++;
      return HttpResponse.json(report);
    }),
  );
  renderApp(
    `/reports/${report.report.id}?version=2&map_view=view-1&map_revision=revision-1`,
    'user',
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('exact report version');
  expect(reports).toBe(0);
  expect(screen.queryByRole('heading', { name: 'Map and timeline' })).not.toBeInTheDocument();
});

it.each([true, false])(
  'reflects active team creation rights, including a colleague’s report (active=%s)',
  async (active) => {
    const team = { ...roster.team, is_active: active };
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
      http.get('/api/teams/:id', () =>
        HttpResponse.json({
          ...roster,
          team,
          members: [
            {
              ...roster.members[0],
              user_id: plainUser.id,
              account_role: 'user',
              role: 'member',
              is_active: true,
            },
          ],
        }),
      ),
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          report: { ...report.report, team_id: team.id, created_by: adminUser.id },
        }),
      ),
    );
    renderApp(`/reports/${report.report.id}`, 'user');
    await screen.findByRole('heading', { name: 'Map and timeline' });
    if (active) expect(await screen.findByRole('button', { name: 'Save map view' })).toBeEnabled();
    else expect(screen.queryByRole('button', { name: 'Save map view' })).not.toBeInTheDocument();
  },
);

it('aborts the anchored report request when its identity changes', async () => {
  let started = false,
    aborted = false;
  let finish: () => void = () => undefined;
  const done = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => HttpResponse.json(saved)),
    http.get('/api/reports/:id', async ({ request }) => {
      started = true;
      request.signal.addEventListener('abort', () => {
        aborted = true;
      });
      await done;
      return HttpResponse.json(report);
    }),
  );
  const view = renderApp(
    `/reports/${report.report.id}?version=1&map_view=view-1&map_revision=revision-1`,
    'user',
  );
  await waitFor(() => expect(started).toBe(true));
  act(() => applySession('anonymous'));
  await waitFor(() => expect(aborted).toBe(true));
  finish();
  view.unmount();
});

it('keeps an owned map in an archived team readable without offering writes', async () => {
  const team = { ...roster.team, is_active: false };
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
    http.get('/api/map/views/:view/revisions/:revision', () =>
      HttpResponse.json({ ...saved, view: { ...saved.view, team_id: team.id } }),
    ),
    http.get('/api/reports/:id', () =>
      HttpResponse.json({
        ...report,
        report: { ...report.report, team_id: team.id, created_by: plainUser.id },
      }),
    ),
  );
  renderApp(
    `/reports/${report.report.id}?version=1&map_view=view-1&map_revision=revision-1`,
    'user',
  );
  await screen.findByRole('heading', { name: 'Map and timeline' });
  expect(screen.getByLabelText('Map view title')).toHaveValue('Saved geography');
  for (const name of ['Save separate copy', 'Save new revision', 'Archive view'])
    expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
});

it('opens the anchored report when a retained overlay cannot be displayed', async () => {
  const overlay = {
    ...saved.revision.state.overlays[0]!,
    visible: true,
    geometry: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [0, 0],
                [2, 2],
                [0, 2],
                [2, 0],
                [0, 0],
              ],
            ],
          },
        },
      ],
    },
  };
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () =>
      HttpResponse.json({
        ...saved,
        revision: { ...saved.revision, state: { ...saved.revision.state, overlays: [overlay] } },
      }),
    ),
  );
  renderApp(
    `/reports/${report.report.id}?version=1&map_view=view-1&map_revision=revision-1`,
    'user',
  );
  await screen.findByRole('heading', { name: 'Map and timeline' });
  expect(screen.getByLabelText('Map view title')).toHaveValue('Saved geography');
  expect(screen.getByRole('button', { name: 'Open evidence map' })).toBeVisible();
});
