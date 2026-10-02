import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import * as download from '@/lib/download';
import { server } from '@/test/server';
import { ForecastPanel } from './ForecastPanel';
import { forecastFixture, reviewedClaim } from './forecastTestFixtures';

const path = '/api/reports/report-1/versions/3/ledgers';
const page = (items: unknown[]) =>
  HttpResponse.json({ items, total: items.length, limit: 20, offset: 0 });
const open = async () => {
  render(<ForecastPanel reportId="report-1" version={3} canEdit />);
  await userEvent.click(screen.getByRole('button', { name: 'Forecasts and review history' }));
};

it('creates from an exact reviewed revision and preserves the report version and passage', async () => {
  let items: unknown[] = [];
  let submitted: Record<string, unknown> | null = null;
  server.use(
    http.get(path, () => page(items)),
    http.get('/api/claims', () => page([reviewedClaim])),
    http.post(`${path}/forecasts`, async ({ request }) => {
      submitted = (await request.json()) as Record<string, unknown>;
      items = [forecastFixture];
      return HttpResponse.json(forecastFixture, { status: 201 });
    }),
  );
  await open();
  await userEvent.click(
    await screen.findByRole('button', { name: 'Create forecast from a reviewed claim' }),
  );
  await userEvent.selectOptions(
    await screen.findByLabelText('Exact reviewed claim revision'),
    'reviewed-1',
  );
  await userEvent.type(screen.getByLabelText('Resolution criterion'), 'Road stays open');
  fireEvent.change(screen.getByLabelText('Review date and time'), {
    target: { value: '2027-01-02T12:00' },
  });
  fireEvent.change(screen.getByLabelText('Forecast horizon date and time'), {
    target: { value: '2027-01-03T12:00' },
  });
  await userEvent.type(screen.getByLabelText('Confidence limitation'), 'A single source');
  await userEvent.click(screen.getByRole('button', { name: 'Save forecast' }));
  await screen.findByRole('heading', { name: 'Whether the road stays open' });
  expect(screen.queryByRole('button', { name: 'Save forecast' })).not.toBeInTheDocument();
  expect(submitted).toMatchObject({
    claim_id: 'claim-1',
    claim_revision_id: 'reviewed-1',
    supporting: [{ evidence_label: 'E1', excerpt_sha256: 'a'.repeat(64) }],
    likelihood: 'realistic_possibility',
  });
});

it('records an unresolved review with the exact version token and shows append-only history', async () => {
  let value = forecastFixture;
  let submitted: unknown;
  server.use(
    http.get(path, () => page([value])),
    http.post(`${path}/ledger-1/reviews`, async ({ request }) => {
      submitted = await request.json();
      value = {
        ...forecastFixture,
        history: {
          ...forecastFixture.history,
          decisions: [
            {
              id: 'review-1',
              forecast_version_id: 'forecast-v1',
              previous_decision_id: null,
              recorded_at: '2026-02-01T00:00:00Z',
              state: 'unresolved',
              method: 'reviewer',
              actor_id: 'reviewer-1',
              reason: 'No later observation',
              evidence: [],
              outcome: null,
              observation: null,
              corrects_decision_id: null,
              superseding_version_id: null,
            },
          ],
        },
      };
      return HttpResponse.json(value);
    }),
  );
  await open();
  await userEvent.click(await screen.findByRole('button', { name: 'Review forecast' }));
  await userEvent.type(screen.getByLabelText('Review reason'), 'No later observation');
  await userEvent.click(screen.getByRole('button', { name: 'Record review' }));
  expect(await screen.findByText(/Outcome state: unresolved/)).toBeInTheDocument();
  expect(submitted).toMatchObject({
    state: 'unresolved',
    outcome: null,
    expected_version_id: 'forecast-v1',
    previous_decision_id: null,
    outcome_evidence: [],
  });
  await userEvent.click(screen.getByText('Immutable forecast history'));
  expect(screen.getByText(/No later observation/)).toBeInTheDocument();
});

it('requires selected histories before a separate exact-version export', async () => {
  const save = vi.spyOn(download, 'saveTextFile').mockImplementation(() => undefined);
  let submitted: unknown;
  server.use(
    http.get(path, () => page([forecastFixture])),
    http.post(`${path}/exports/forecasts`, async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json([forecastFixture]);
    }),
  );
  await open();
  expect(
    await screen.findByRole('button', { name: 'Export selected forecast histories' }),
  ).toBeDisabled();
  await userEvent.click(
    screen.getByLabelText('Include this forecast history in a separate JSON export'),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Export selected forecast histories' }));
  await waitFor(() => expect(save).toHaveBeenCalledOnce());
  expect(submitted).toEqual({ ledger_ids: ['ledger-1'] });
  expect(save.mock.calls[0]?.[1]).toContain('"report_version": 3');
  save.mockRestore();
});

it('removes private forecast history and unfinished reviews on access loss', async () => {
  let denied = false;
  server.use(
    http.get(path, () =>
      denied
        ? HttpResponse.json(
            { error: { code: 'not_found', message: 'Report unavailable' } },
            { status: 404 },
          )
        : page([forecastFixture]),
    ),
  );
  await open();
  await userEvent.click(await screen.findByRole('button', { name: 'Review forecast' }));
  await userEvent.type(screen.getByLabelText('Review reason'), 'Private unfinished review');
  denied = true;
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByDisplayValue('Private unfinished review')).not.toBeInTheDocument();
  expect(await screen.findByRole('alert')).toHaveTextContent('Forecasts unavailable');
  expect(screen.queryByText('Whether the road stays open')).not.toBeInTheDocument();
});
