import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { server } from '@/test/server';
import { ForecastPanel } from './ForecastPanel';
import { OutcomeCounts } from './ForecastWatches';
import { forecastFixture, reviewedClaim } from './forecastTestFixtures';

const path = '/api/reports/report-1/versions/3/ledgers';
const page = (items: unknown[]) =>
  HttpResponse.json({ items, total: items.length, limit: 20, offset: 0 });

it('requires a later exact reviewed passage for resolved outcomes', async () => {
  let submitted: unknown;
  const laterId = '11111111-1111-4111-8111-111111111111';
  const later = {
    ...reviewedClaim,
    id: 'later-review',
    claim_id: 'later-claim',
    report_id: laterId,
  };
  server.use(
    http.get(path, () => page([forecastFixture])),
    http.get('/api/claims', ({ request }) => {
      expect(new URL(request.url).searchParams.get('report_id')).toBe(laterId);
      expect(new URL(request.url).searchParams.get('version_number')).toBe('2');
      return page([later]);
    }),
    http.post(`${path}/ledger-1/reviews`, async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json(forecastFixture);
    }),
  );
  render(<ForecastPanel reportId="report-1" version={3} canEdit />);
  await userEvent.click(screen.getByRole('button', { name: 'Forecasts and review history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Review forecast' }));
  await userEvent.selectOptions(screen.getByLabelText('Review decision'), 'true');
  expect(screen.getByRole('button', { name: 'Record review' })).toBeDisabled();
  await userEvent.type(
    screen.getByLabelText('Review reason'),
    'Later independently reviewed evidence',
  );
  await userEvent.type(
    screen.getByLabelText('Later report link'),
    `https://example.com/reports/${laterId}`,
  );
  fireEvent.change(screen.getByLabelText('Later report version'), { target: { value: '2' } });
  await userEvent.click(screen.getByRole('button', { name: 'Load later reviewed claims' }));
  await userEvent.selectOptions(
    await screen.findByLabelText('Exact reviewed claim revision'),
    'later-review',
  );
  await userEvent.selectOptions(
    screen.getByLabelText('Outcome evidence passage'),
    'E1:' + 'a'.repeat(64),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Record review' }));
  await waitFor(() =>
    expect(submitted).toMatchObject({
      state: 'resolved',
      outcome: true,
      expected_version_id: 'forecast-v1',
      outcome_evidence: [
        {
          report_id: laterId,
          version: 2,
          claim_id: 'later-claim',
          claim_revision_id: 'later-review',
          citation: { evidence_label: 'E1', excerpt_sha256: 'a'.repeat(64) },
        },
      ],
    }),
  );
});

it('supersedes with the original claim anchor and an optimistic version token', async () => {
  let submitted: unknown;
  server.use(
    http.get(path, () => page([forecastFixture])),
    http.post(`${path}/ledger-1/supersessions`, async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json(forecastFixture);
    }),
  );
  render(<ForecastPanel reportId="report-1" version={3} canEdit />);
  await userEvent.click(screen.getByRole('button', { name: 'Forecasts and review history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Supersede forecast' }));
  fireEvent.change(screen.getByLabelText('Review date and time'), {
    target: { value: '2027-02-01T12:00' },
  });
  fireEvent.change(screen.getByLabelText('Forecast horizon date and time'), {
    target: { value: '2027-03-01T12:00' },
  });
  await userEvent.selectOptions(screen.getByLabelText('Original PHIA likelihood band'), 'likely');
  await userEvent.type(screen.getByLabelText('Supersession reason'), 'Changed assumptions');
  await userEvent.click(screen.getByRole('button', { name: 'Save replacement forecast' }));
  await waitFor(() =>
    expect(submitted).toMatchObject({
      expected_version_id: 'forecast-v1',
      reason: 'Changed assumptions',
      replacement: { claim_id: 'claim-1', claim_revision_id: 'reviewed-1', likelihood: 'likely' },
    }),
  );
});

const counts = {
  since: '2026-01-01T00:00:00Z',
  until: '2026-10-01T00:00:00Z',
  forecast_versions: 10,
  counting_unit: 'forecast version, by issue time, using its latest decision once',
  caveat:
    'Related versions may not be independent observations. The cohort can be small or selective. PHIA bands are not calibrated probabilities.',
  bands: [
    {
      likelihood: 'realistic_possibility',
      resolved_true: 3,
      resolved_false: 2,
      unresolved: 2,
      open: 1,
      due: 1,
      superseded: 1,
      resolved_denominator: 5,
    },
  ],
};

it('shows exact counts, original band, cohort and resolved denominator without percentages', async () => {
  server.use(
    http.get('/api/forecasts/counts', ({ request }) => {
      expect(new URL(request.url).searchParams.get('team_id')).toBe('team-1');
      return HttpResponse.json(counts);
    }),
  );
  render(<OutcomeCounts teamId="team-1" />);
  expect(screen.getByText('Loading forecast outcome counts')).toBeInTheDocument();
  const row = await screen.findByRole('row', { name: 'realistic possibility 3 2 2 1 1 1 5' });
  expect(
    within(row)
      .getAllByRole('cell')
      .map((cell) => cell.textContent),
  ).toEqual(['realistic possibility', '3', '2', '2', '1', '1', '1', '5']);
  expect(screen.getByText(/Counting unit: forecast version/)).toBeInTheDocument();
  expect(screen.getByText(/PHIA bands are not calibrated probabilities/)).toBeInTheDocument();
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
});

it('shows empty outcomes explicitly and clears counts when access is lost', async () => {
  let denied = false;
  server.use(
    http.get('/api/forecasts/counts', () =>
      denied
        ? HttpResponse.json(
            { error: { code: 'not_found', message: 'Workspace unavailable' } },
            { status: 404 },
          )
        : HttpResponse.json({ ...counts, forecast_versions: 0, bands: [] }),
    ),
  );
  render(<OutcomeCounts teamId="team-1" />);
  expect(
    await screen.findByText('No forecast versions in this scope and issue-time window.'),
  ).toBeInTheDocument();
  expect(screen.getByText(/No resolved outcomes in this cohort/)).toBeInTheDocument();
  denied = true;
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByText(/No resolved outcomes in this cohort/)).not.toBeInTheDocument();
  expect(await screen.findByRole('alert')).toHaveTextContent('Outcome counts unavailable');
});
