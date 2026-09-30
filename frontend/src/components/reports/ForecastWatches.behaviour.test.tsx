import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import type { TeamDetail } from '@/lib/api/teams';
import { watchSchema } from '@/lib/api/forecastSchemas';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { server } from '@/test/server';
import { ForecastWatches, OutcomeCounts } from './ForecastWatches';

const team: TeamDetail = {
  team: {
    id: 'team-1',
    name: 'Northern desk',
    is_active: true,
    created_by: 'owner-1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    description: null,
  },
  members: [],
};
const archived = {
  ...team,
  team: { ...team.team, id: 'team-2', name: 'Archive', is_active: false },
};
const workspaces = (overrides: Partial<Workspaces> = {}): Workspaces => ({
  key: 'roster-1',
  data: [team, archived],
  teams: [team, archived],
  error: null,
  loading: false,
  loader: () => Promise.resolve([team, archived]),
  reload: () => Promise.resolve(),
  refresh: () => Promise.resolve(),
  setData: () => undefined,
  label: () => 'Personal',
  canManage: () => false,
  canAcknowledge: () => true,
  ...overrides,
});
const watch = watchSchema.parse({
  ledger_id: 'ledger-1',
  report_id: 'report-1',
  report_version: 3,
  title: 'Road access judgement',
  version_id: 'forecast-1',
  review_at: '2026-09-01T12:00:00Z',
  horizon_end: '2026-10-01T12:00:00Z',
  state: 'open',
  review_due: true,
  reminded_at: '2026-09-02T12:00:00Z',
  team_id: null,
});
const counts = {
  since: '2026-01-01T00:00:00Z',
  until: '2026-10-01T00:00:00Z',
  forecast_versions: 1,
  counting_unit: 'forecast version',
  caveat: 'PHIA bands are not calibrated probabilities.',
  bands: [
    {
      likelihood: 'likely',
      resolved_true: 1,
      resolved_false: 0,
      unresolved: 0,
      open: 0,
      due: 0,
      superseded: 0,
      resolved_denominator: 1,
    },
  ],
};
const page = (items = [watch], total = items.length, offset = 0) => ({
  items,
  total,
  limit: 20,
  offset,
});
const unavailable = () =>
  HttpResponse.json(
    { error: { code: 'not_found', message: 'Workspace unavailable' } },
    { status: 404 },
  );
function handlers() {
  const requests = { watches: [] as URL[], counts: [] as URL[] };
  server.use(
    http.get('/api/forecasts/watches', ({ request }) => {
      requests.watches.push(new URL(request.url));
      return HttpResponse.json(page());
    }),
    http.get('/api/forecasts/counts', ({ request }) => {
      requests.counts.push(new URL(request.url));
      return HttpResponse.json(counts);
    }),
  );
  return requests;
}
function view(scope = workspaces()) {
  return (
    <MemoryRouter>
      <ForecastWatches workspaces={scope} />
    </MemoryRouter>
  );
}
async function open() {
  await userEvent.click(
    screen.getByRole('button', { name: 'Forecast watches and outcome counts' }),
  );
}

it('loads only when opened, distinguishes review state and retains exact report links', async () => {
  const requests = handlers();
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let watchRequests = 0;
  server.use(
    http.get('/api/forecasts/watches', async () => {
      watchRequests += 1;
      await gate;
      return HttpResponse.json(
        page([
          watch,
          {
            ...watch,
            ledger_id: 'ledger-2',
            title: 'Later review',
            review_due: false,
            reminded_at: null,
          },
        ]),
      );
    }),
  );
  try {
    render(view());
    expect(requests.counts).toHaveLength(0);
    expect(watchRequests).toBe(0);
    expect(screen.queryByLabelText('Forecast workspace')).not.toBeInTheDocument();
    await open();
    expect(screen.getByText('Loading forecast watches')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Archive (archived)' })).toBeInTheDocument();
    await act(async () => {
      release();
      await gate;
    });
    expect(
      await screen.findByRole('link', { name: 'Road access judgement, report version 3' }),
    ).toHaveAttribute('href', '/reports/report-1?version=3');
    expect(screen.getByText(/^Review due:/)).toBeInTheDocument();
    expect(screen.getByText(/^Review scheduled or completed:/)).toBeInTheDocument();
    expect(screen.getAllByText(/^Reminder first raised/)).toHaveLength(1);
    expect(screen.getAllByText(/^Outcome state: open. Horizon:/)).toHaveLength(2);
    await waitFor(() => expect(requests.counts).toHaveLength(1));
    expect(requests.counts[0]?.searchParams.get('personal')).toBe('true');
    await open();
    expect(
      screen.getByRole('button', { name: 'Forecast watches and outcome counts' }),
    ).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  } finally {
    release();
  }
});

it('paginates both ways and resets the page when switching to a team', async () => {
  handlers();
  const queries: URLSearchParams[] = [];
  server.use(
    http.get('/api/forecasts/watches', ({ request }) => {
      const query = new URL(request.url).searchParams;
      queries.push(query);
      const offset = Number(query.get('offset'));
      return HttpResponse.json(
        page(
          [{ ...watch, title: `${query.get('team_id') ?? 'Personal'} page ${offset}` }],
          21,
          offset,
        ),
      );
    }),
  );
  render(view());
  await open();
  await screen.findByRole('link', { name: 'Personal page 0, report version 3' });
  expect(screen.getByRole('button', { name: 'Previous watches' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Next watches' }));
  await screen.findByRole('link', { name: 'Personal page 20, report version 3' });
  expect(screen.getByRole('button', { name: 'Next watches' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Previous watches' }));
  await screen.findByRole('link', { name: 'Personal page 0, report version 3' });
  await userEvent.click(screen.getByRole('button', { name: 'Next watches' }));
  await screen.findByRole('link', { name: 'Personal page 20, report version 3' });
  await userEvent.selectOptions(screen.getByLabelText('Forecast workspace'), 'team-1');
  await screen.findByRole('link', { name: 'team-1 page 0, report version 3' });
  expect(queries.map((query) => query.get('offset'))).toEqual(['0', '20', '0', '20', '0']);
  expect(queries.at(-1)?.get('team_id')).toBe('team-1');
  expect(queries.at(-1)?.has('personal')).toBe(false);
  expect(screen.getByRole('button', { name: 'Previous watches' })).toBeDisabled();
});

it('shows empty watches and a cohort without resolved observations without pagination', async () => {
  handlers();
  server.use(
    http.get('/api/forecasts/watches', () => HttpResponse.json(page([], 0))),
    http.get('/api/forecasts/counts', () =>
      HttpResponse.json({ ...counts, forecast_versions: 0, bands: [] }),
    ),
  );
  render(view());
  await open();
  expect(await screen.findByText('No forecast watches in this scope.')).toBeInTheDocument();
  expect(
    await screen.findByText('No forecast versions in this scope and issue-time window.'),
  ).toBeInTheDocument();
  expect(screen.getByText(/No resolved outcomes in this cohort/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Next watches' })).not.toBeInTheDocument();
});

it('reports a watch failure while leaving independently available counts readable', async () => {
  handlers();
  server.use(http.get('/api/forecasts/watches', unavailable));
  render(view());
  await open();
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Forecast watches unavailable: Workspace unavailable',
  );
  expect(await screen.findByRole('row', { name: 'likely 1 0 0 0 0 0 1' })).toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

it('hides selected team watches during roster refresh and after membership disappears', async () => {
  handlers();
  const rendered = render(view());
  await open();
  await userEvent.selectOptions(screen.getByLabelText('Forecast workspace'), 'team-1');
  await screen.findByRole('link');
  rendered.rerender(view(workspaces({ loading: true })));
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  rendered.rerender(view(workspaces()));
  await screen.findByRole('link');
  rendered.rerender(view(workspaces({ teams: [] })));
  expect(screen.getByRole('alert')).toHaveTextContent(
    'The selected workspace is no longer accessible.',
  );
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

it('removes private watches and counts immediately when current access is invalidated', async () => {
  handlers();
  render(view());
  await open();
  await screen.findByRole('link');
  await screen.findByRole('row', { name: 'likely 1 0 0 0 0 0 1' });
  server.use(
    http.get('/api/forecasts/watches', unavailable),
    http.get('/api/forecasts/counts', unavailable),
  );
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(2));
  expect(screen.getByText(/Outcome counts unavailable/)).toBeInTheDocument();
});

it('does not show a delayed team result after the workspace identity changes', async () => {
  handlers();
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let pendingSignal: AbortSignal | undefined;
  server.use(
    http.get('/api/forecasts/watches', async ({ request }) => {
      if (new URL(request.url).searchParams.has('team_id')) {
        pendingSignal = request.signal;
        await gate;
        return HttpResponse.json(page([{ ...watch, title: 'Private delayed judgement' }]));
      }
      return HttpResponse.json(page([{ ...watch, title: 'Personal judgement' }]));
    }),
  );
  try {
    const rendered = render(view());
    await open();
    await screen.findByRole('link', { name: 'Personal judgement, report version 3' });
    await userEvent.selectOptions(screen.getByLabelText('Forecast workspace'), 'team-1');
    await waitFor(() => expect(pendingSignal).toBeDefined());
    rendered.rerender(view(workspaces({ key: 'roster-2' })));
    expect(pendingSignal?.aborted).toBe(true);
    expect(screen.getByLabelText('Forecast workspace')).toHaveValue('');
    await screen.findByRole('link', { name: 'Personal judgement, report version 3' });
    await act(async () => {
      release();
      await gate;
    });
    expect(screen.queryByText(/Private delayed judgement/)).not.toBeInTheDocument();
  } finally {
    release();
  }
});

it('requests the selected UTC cohort boundaries and replaces stale counts with an error', async () => {
  handlers();
  const queries: URLSearchParams[] = [];
  server.use(
    http.get('/api/forecasts/counts', ({ request }) => {
      const query = new URL(request.url).searchParams;
      queries.push(query);
      if (query.get('until') === '2026-01-01T00:00:00Z') {
        return HttpResponse.json(
          { error: { code: 'invalid_request', message: 'End must follow start' } },
          { status: 422 },
        );
      }
      return HttpResponse.json(counts);
    }),
  );
  render(<OutcomeCounts teamId="team-1" />);
  const row = await screen.findByRole('row', { name: 'likely 1 0 0 0 0 0 1' });
  expect(within(row).getAllByRole('cell')).toHaveLength(8);
  fireEvent.change(screen.getByLabelText('Issued on or after (UTC)'), {
    target: { value: '2026-03-01' },
  });
  fireEvent.change(screen.getByLabelText('Issued before (UTC)'), {
    target: { value: '2026-04-01' },
  });
  await waitFor(() => expect(queries.at(-1)?.get('until')).toBe('2026-04-01T00:00:00Z'));
  expect(queries.at(-1)?.get('since')).toBe('2026-03-01T00:00:00Z');
  expect(queries.at(-1)?.get('team_id')).toBe('team-1');
  fireEvent.change(screen.getByLabelText('Issued before (UTC)'), {
    target: { value: '2026-01-01' },
  });
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Outcome counts unavailable: End must follow start',
  );
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
