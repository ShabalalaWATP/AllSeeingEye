import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('opens the selected subscription history and links its durable edition', async () => {
  const editionId = 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1';
  const reportId = 'd2d2d2d2-d2d2-42d2-82d2-d2d2d2d2d2d2';
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/events', () =>
      HttpResponse.json({
        items: [
          {
            id: 'a4a4a4a4-a4a4-44a4-84a4-a4a4a4a4a4a4',
            edition_id: editionId,
            event_kind: 'material_change',
            created_at: '2026-09-14T06:01:00Z',
          },
        ],
        limit: 10,
        offset: 0,
      }),
    ),
    http.get('/api/schedules/:id/editions', () =>
      HttpResponse.json({
        limit: 10,
        offset: 0,
        items: [
          {
            id: editionId,
            subscription_id: schedule.id,
            trigger: 'scheduled',
            due_at_utc: '2026-09-14T06:00:00Z',
            frozen_revision: 1,
            requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
            effective_intervals: [{ start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' }],
            gaps: [],
            workflow: 'completed',
            report_quality: 'ready',
            coverage: 'complete_for_plan',
            job_id: null,
            report_id: reportId,
            version_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
            comparison: {
              previous_version_id: 'f4f4f4f4-f4f4-44f4-84f4-f4f4f4f4f4f4',
              current_version_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
              state: 'assessment_changed',
              reasons: ['likelihood_changed'],
              changed_claims: 1,
              corrected_evidence: 0,
              novel_evidence: 2,
              syndicated_duplicates: 3,
              summary: 'The assessment changed between exact versions.',
            },
            safe_reason: null,
            created_at: '2026-09-14T06:00:00Z',
            updated_at: '2026-09-14T06:01:00Z',
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/research/recurring', 'user');
  await user.click(await screen.findByRole('button', { name: 'History' }));
  const history = await screen.findByRole('region', { name: 'Subscription history' });
  expect(within(history).getByText('Ready')).toBeVisible();
  expect(within(history).getByRole('link', { name: 'Read report' })).toHaveAttribute(
    'href',
    `/reports/${reportId}`,
  );
  expect(within(history).getByText('Compared with the previous report')).toBeVisible();
  expect(within(history).getByText('The assessment changed between exact versions.')).toBeVisible();
  expect(within(history).getByText(/2 new captured items/)).toBeVisible();
  await user.click(within(history).getByRole('button', { name: 'Activity' }));
  expect(await within(history).findByText('Material change identified')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'History' }));
  expect(screen.queryByRole('region', { name: 'Subscription history' })).not.toBeInTheDocument();
});

it('runs a subscription now with one stable request ID across a failed retry', async () => {
  const requestIds: string[] = [];
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.post('/api/schedules/:id/run-now', async ({ request }) => {
      const body = (await request.json()) as { request_id: string };
      requestIds.push(body.request_id);
      if (requestIds.length === 1) {
        return HttpResponse.json(
          { error: { code: 'temporarily_unavailable', message: 'Please retry.' } },
          { status: 503 },
        );
      }
      return HttpResponse.json({
        id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
        subscription_id: schedule.id,
        trigger: 'run_now',
        due_at_utc: null,
        frozen_revision: 1,
        requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
        effective_intervals: [],
        gaps: [],
        workflow: 'queued',
        report_quality: 'absent',
        coverage: 'unknown',
        job_id: null,
        report_id: null,
        version_id: null,
        safe_reason: null,
        created_at: '2026-09-14T06:00:00Z',
        updated_at: '2026-09-14T06:00:00Z',
      });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  await user.click(await screen.findByRole('button', { name: 'Run now' }));
  expect(await screen.findByText('Please retry.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Run now' }));
  expect(await screen.findByText(/A new report has been queued/)).toBeVisible();
  expect(requestIds).toHaveLength(2);
  expect(requestIds[0]).toBe(requestIds[1]);
});

it('offers retained edition pause and resume controls to its owner', async () => {
  let workflow = 'queued';
  const edition = {
    id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
    subscription_id: schedule.id,
    trigger: 'scheduled',
    due_at_utc: '2026-09-14T06:00:00Z',
    frozen_revision: 1,
    requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
    effective_intervals: [],
    gaps: [],
    report_quality: 'absent',
    coverage: 'unknown',
    job_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
    report_id: null,
    version_id: null,
    safe_reason: null,
    created_at: '2026-09-14T06:00:00Z',
    updated_at: '2026-09-14T06:00:00Z',
  };
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/editions', () =>
      HttpResponse.json({ items: [{ ...edition, workflow }], limit: 10, offset: 0 }),
    ),
    http.post('/api/schedules/:id/editions/:editionId/pause', () => {
      workflow = 'paused';
      return HttpResponse.json({ ...edition, workflow });
    }),
    http.post('/api/schedules/:id/editions/:editionId/resume', () => {
      workflow = 'queued';
      return HttpResponse.json({ ...edition, workflow });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  await user.click(await screen.findByRole('button', { name: 'History' }));
  const history = await screen.findByRole('region', { name: 'Subscription history' });
  await user.click(await within(history).findByRole('button', { name: 'Pause edition' }));
  await user.click(await within(history).findByRole('button', { name: 'Resume edition' }));
  expect(await within(history).findByRole('button', { name: 'Pause edition' })).toBeEnabled();
});

it('confirms an eligible partial edition as comparison baseline without hiding its gaps', async () => {
  let accepted = false;
  let writes = 0;
  const edition = {
    id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
    subscription_id: schedule.id,
    trigger: 'scheduled',
    due_at_utc: '2026-09-14T06:00:00Z',
    frozen_revision: 1,
    requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
    effective_intervals: [],
    gaps: [{ start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' }],
    workflow: 'completed',
    report_quality: 'needs_review',
    coverage: 'partial',
    job_id: null,
    report_id: 'd2d2d2d2-d2d2-42d2-82d2-d2d2d2d2d2d2',
    version_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
    safe_reason: null,
    created_at: '2026-09-14T06:00:00Z',
    updated_at: '2026-09-14T06:01:00Z',
  };
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.get('/api/schedules/:id/editions', () =>
      HttpResponse.json({
        items: [{ ...edition, accepted_as_baseline: accepted }],
        limit: 10,
        offset: 0,
      }),
    ),
    http.post('/api/schedules/:id/editions/:editionId/accept-baseline', () => {
      writes++;
      accepted = true;
      return HttpResponse.json({
        subscription_id: schedule.id,
        edition_id: edition.id,
        analytical_baseline_version_id: edition.version_id,
        covered_intervals: [],
        complete_cutoff: null,
      });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  await user.click(await screen.findByRole('button', { name: 'History' }));
  const history = await screen.findByRole('region', { name: 'Subscription history' });
  await user.click(
    await within(history).findByRole('button', { name: 'Use as comparison baseline' }),
  );
  expect(writes).toBe(0);
  expect(within(history).getByText(/Missing coverage will stay marked as missing/)).toBeVisible();
  await user.click(within(history).getByRole('button', { name: 'Confirm baseline' }));
  expect(await within(history).findByText('Accepted for comparison')).toBeVisible();
  expect(writes).toBe(1);
  expect(within(history).queryByRole('button', { name: 'Use as comparison baseline' })).toBeNull();
});
