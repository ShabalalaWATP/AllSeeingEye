import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const base = {
  subscription_id: schedule.id,
  trigger: 'scheduled',
  frozen_revision: 1,
  requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
  effective_intervals: [],
  gaps: [],
  report_quality: 'absent',
  coverage: 'unknown',
  job_id: null,
  report_id: null,
  version_id: null,
  comparison: null,
  safe_reason: null,
  due_at_utc: null,
  created_at: '2026-09-14T06:00:00Z',
  updated_at: '2026-09-14T06:01:00Z',
};

function edition(index: number, changes: Record<string, unknown>) {
  const suffix = String(index).padStart(12, '0');
  return { ...base, id: `a0a0a0a0-a0a0-40a0-80a0-${suffix}`, ...changes };
}

const jobId = 'b1b1b1b1-b1b1-41b1-81b1-b1b1b1b1b1b1';

async function openHistory() {
  const { user } = renderApp('/research/recurring', 'user');
  await user.click(await screen.findByRole('button', { name: 'History' }));
  return { user, history: await screen.findByRole('region', { name: 'Subscription history' }) };
}

it('labels every edition state, pages older editions and retries a waiting edition', async () => {
  const first = [
    edition(1, {
      workflow: 'completed',
      report_quality: 'needs_review',
      report_id: 'c2c2c2c2-c2c2-42c2-82c2-c2c2c2c2c2c2',
    }),
    edition(2, { workflow: 'completed', report_quality: 'ready', coverage: 'partial' }),
    edition(3, { workflow: 'pending', safe_reason: 'capacity_wait' }),
    edition(4, { workflow: 'retry_wait', job_id: jobId }),
    edition(5, { workflow: 'blocked' }),
    edition(6, { workflow: 'failed' }),
    edition(7, { workflow: 'cancelled' }),
    edition(8, { workflow: 'skipped' }),
    edition(9, { workflow: 'running', job_id: 'd3d3d3d3-d3d3-43d3-83d3-d3d3d3d3d3d3' }),
    edition(10, {
      workflow: 'queued',
      comparison: {
        previous_version_id: null,
        current_version_id: 'e4e4e4e4-e4e4-44e4-84e4-e4e4e4e4e4e4',
        state: 'insufficient_coverage',
        reasons: ['baseline_unavailable'],
        changed_claims: 0,
        corrected_evidence: 1,
        novel_evidence: 0,
        syndicated_duplicates: 0,
        summary: 'No earlier edition to compare.',
      },
    }),
  ];
  const older = [
    edition(11, { workflow: 'completed', report_quality: 'ready', coverage: 'complete_for_plan' }),
  ];
  let retried = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/events', () =>
      HttpResponse.json({ items: [], limit: 10, offset: 0 }),
    ),
    http.get('/api/schedules/:id/editions', ({ request }) => {
      const offset = new URL(request.url).searchParams.get('offset');
      return HttpResponse.json({
        limit: 10,
        offset: Number(offset),
        items: offset === '0' ? first : older,
      });
    }),
    http.post('/api/schedules/:id/editions/:edition/retry', () => {
      retried += 1;
      return HttpResponse.json({ ...first[3], workflow: 'queued' });
    }),
  );
  const { user, history } = await openHistory();
  const panel = within(history);
  await panel.findByText('Needs review');
  for (const label of [
    'Partial coverage',
    'Waiting for capacity',
    'Waiting to retry',
    'Blocked',
    'Failed',
    'Cancelled',
    'Skipped',
    'Running',
    'Queued',
  ])
    expect(panel.getByText(label)).toBeVisible();
  expect(panel.getByText('Waiting for queue space')).toBeVisible();
  expect(panel.getAllByRole('link', { name: 'View progress' })[0]).toHaveAttribute(
    'href',
    `/research/jobs/${jobId}`,
  );
  expect(panel.getAllByText('Pending admission').length).toBeGreaterThan(0);
  expect(panel.getByText('Comparison status')).toBeVisible();
  expect(
    panel.getByText(/0 changed assessments · 1 source correction · 0 new captured items/),
  ).toBeVisible();

  await user.click(panel.getByRole('button', { name: 'Retry edition' }));
  await waitFor(() => expect(retried).toBe(1));

  await user.click(panel.getByRole('button', { name: 'Load older editions' }));
  await waitFor(() => expect(panel.getAllByText('Ready').length).toBeGreaterThan(0));
  expect(panel.queryByRole('button', { name: 'Load older editions' })).not.toBeInTheDocument();
});

it('shows an edition whose claim mapping could not be resolved', async () => {
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/events', () =>
      HttpResponse.json({ items: [], limit: 10, offset: 0 }),
    ),
    http.get('/api/schedules/:id/editions', () =>
      HttpResponse.json({
        limit: 10,
        offset: 0,
        items: [
          edition(1, {
            workflow: 'completed',
            report_quality: 'ready',
            comparison: {
              previous_version_id: 'f5f5f5f5-f5f5-45f5-85f5-f5f5f5f5f5f5',
              current_version_id: 'e4e4e4e4-e4e4-44e4-84e4-e4e4e4e4e4e4',
              state: 'assessment_changed',
              reasons: ['claim_mapping_unresolved', 'claim_inventory_changed'],
              changed_claims: 2,
              corrected_evidence: 0,
              novel_evidence: 1,
              syndicated_duplicates: 0,
              summary: 'Claims could not be matched to the earlier edition.',
            },
          }),
        ],
      }),
    ),
  );
  const { history } = await openHistory();
  const panel = within(history);
  expect(
    await panel.findByText('Claims could not be matched to the earlier edition.'),
  ).toBeVisible();
  expect(panel.getByText(/2 changed assessments · 0 source corrections/)).toBeVisible();
  expect(panel.queryByRole('alert')).not.toBeInTheDocument();
});

it('shows empty history, load failures and control failures', async () => {
  let fail = true;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/events', () =>
      HttpResponse.json({ items: [], limit: 10, offset: 0 }),
    ),
    http.get('/api/schedules/:id/editions', () => {
      if (fail) return HttpResponse.json({ detail: 'Unavailable' }, { status: 503 });
      return HttpResponse.json({
        limit: 10,
        offset: 0,
        items: [edition(1, { workflow: 'paused', job_id: jobId })],
      });
    }),
    http.post('/api/schedules/:id/editions/:edition/resume', () =>
      HttpResponse.json({ detail: 'Conflict' }, { status: 409 }),
    ),
  );
  const { user, history } = await openHistory();
  const panel = within(history);
  expect(await panel.findByRole('alert')).toBeVisible();
  expect(panel.queryByText('No editions have been scheduled yet.')).not.toBeInTheDocument();
  fail = false;
  await user.click(panel.getByRole('button', { name: 'Refresh' }));
  await user.click(await panel.findByRole('button', { name: 'Resume edition' }));
  expect(await panel.findByRole('alert')).toBeVisible();
});
