import { act, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { report } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { DailyBriefing } from './DailyBriefing';
import { DailyBriefingSummary } from './DailyBriefingSummary';

const future = () => new Date(Date.now() + 86_400_000).toISOString();
const briefing = (status: 'running' | 'completed' | 'paused' = 'completed') => ({
  job: reportJob({ status, report_id: status === 'completed' ? report.report.id : null }),
  next_refresh_at: future(),
  coverage_note: 'Only available connected sources are included.',
});
const show = () =>
  render(
    <MemoryRouter>
      <DailyBriefing />
    </MemoryRouter>,
  );
afterEach(() => vi.useRealTimers());

it('shows the daily summary, news, numbered citations and full-report link without model settings', async () => {
  server.use(http.post('/api/live-monitor/briefing', () => HttpResponse.json(briefing())));
  show();
  expect(await screen.findByText('Shelling was reported overnight.')).toBeInTheDocument();
  expect(screen.getByText(/Updated/)).toBeInTheDocument();
  expect(screen.getByText(/Next refresh/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toHaveAttribute(
    'href',
    `/reports/${report.report.id}`,
  );
  expect(screen.queryByText(report.version.model)).not.toBeInTheDocument();
  const user = userEvent.setup();
  await user.click(screen.getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!);
  expect(screen.getByText(/BBC News World:/)).toBeVisible();
  expect(screen.getByText(/TASS English:/)).toHaveTextContent('Ministry statement');
  expect(screen.getAllByRole('link', { name: 'Open source' })).toHaveLength(1);
});

it('polls an existing job to completion without starting another briefing', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const start = vi.fn(() => HttpResponse.json(briefing('running')));
  const read = vi.fn(() => HttpResponse.json(briefing().job));
  server.use(
    http.post('/api/live-monitor/briefing', start),
    http.get('/api/report-jobs/:id', read),
  );
  show();
  await vi.waitFor(() => expect(screen.getByText(/Preparing the latest/)).toBeInTheDocument());
  await act(() => vi.advanceTimersByTimeAsync(5_000));
  await vi.waitFor(() =>
    expect(screen.getByText('Shelling was reported overnight.')).toBeInTheDocument(),
  );
  expect(start).toHaveBeenCalledTimes(1);
  expect(read).toHaveBeenCalledTimes(1);
});

it('keeps paused work explicit and does not silently restart it', async () => {
  const start = vi.fn(() => HttpResponse.json(briefing('paused')));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  expect(await screen.findByText('The daily briefing is paused.')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Review briefing progress' })).toHaveAttribute(
    'href',
    `/research/jobs/${briefing().job.id}`,
  );
  expect(start).toHaveBeenCalledTimes(1);
});

it('offers a deliberate retry after a connection failure', async () => {
  const start = vi
    .fn()
    .mockImplementationOnce(() => apiError(503, 'unavailable', 'Briefing unavailable.'))
    .mockImplementation(() => HttpResponse.json(briefing()));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('Briefing unavailable.');
  await userEvent.setup().click(screen.getByRole('button', { name: 'Retry briefing' }));
  expect(await screen.findByText('Shelling was reported overnight.')).toBeInTheDocument();
  expect(start).toHaveBeenCalledTimes(2);
});

it('clears private briefing content on access changes and waits for a deliberate reload', async () => {
  const start = vi.fn(() => HttpResponse.json(briefing()));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  await screen.findByText('Shelling was reported overnight.');
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByText('Shelling was reported overnight.')).not.toBeInTheDocument();
  expect(await screen.findByRole('alert')).toHaveTextContent('Your access changed');
  expect(start).toHaveBeenCalledTimes(1);
});

it('shows an evidence-gap state and retains review status for an incomplete product', () => {
  render(
    <MemoryRouter>
      <DailyBriefingSummary
        report={{
          ...report,
          version: {
            ...report.version,
            status: 'needs_review',
            body: { ...report.version.body, key_judgements: [], assessment: [], reporting: [] },
          },
        }}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText(/This briefing needs review/)).toBeInTheDocument();
  expect(
    within(screen.getByRole('region', { name: 'Overall situation' })).getByText(
      /not enough evidence/,
    ),
  ).toBeInTheDocument();
  expect(screen.getByText(/No sourced news/)).toBeInTheDocument();
});

it('does not enter an automatic request loop when access is denied', async () => {
  const start = vi.fn(() => apiError(403, 'forbidden', 'Access denied.'));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Your access changed'));
  expect(start).toHaveBeenCalledTimes(1);
});
