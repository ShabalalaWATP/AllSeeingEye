import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const edition = {
  id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
  subscription_id: schedule.id,
  trigger: 'scheduled',
  due_at_utc: '2026-09-14T06:00:00Z',
  frozen_revision: 1,
  requested: { start: '2026-09-13T06:00:00Z', end: '2026-09-14T06:00:00Z' },
  effective_intervals: [],
  gaps: [],
  workflow: 'completed',
  report_quality: 'ready',
  coverage: 'complete_for_plan',
  job_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
  report_id: schedule.last_report_id,
  version_id: schedule.last_version_id,
  safe_reason: null,
  created_at: '2026-09-14T06:00:00Z',
  updated_at: '2026-09-14T06:01:00Z',
};

it.each([null, undefined])(
  'never falls back to latest when the version number is %s',
  async (number) => {
    server.use(
      http.get('/api/schedules', () =>
        HttpResponse.json({
          items: [
            {
              ...schedule,
              last_version_number: number,
              previous_version_number: number,
              last_change: {
                status: 'unchanged',
                report_id: schedule.last_report_id,
                version_id: schedule.last_version_id,
                previous_report_id: schedule.last_report_id,
                previous_version_id: schedule.last_version_id,
                baseline_version_id: null,
                added: 0,
                removed: 0,
                updated: 0,
                reasons: [],
              },
            },
          ],
        }),
      ),
      http.get('/api/schedules/:id/editions', () =>
        HttpResponse.json({
          items: [{ ...edition, version_number: number }],
          limit: 10,
          offset: 0,
        }),
      ),
    );
    const { user } = renderApp('/subscriptions', 'user');
    const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
    expect(table.getByText('Latest edition unavailable')).toBeVisible();
    expect(table.getByText('Previous edition unavailable')).toBeVisible();
    expect(table.queryByRole('link', { name: 'Latest update' })).not.toBeInTheDocument();
    expect(table.queryByRole('link', { name: 'Previous update' })).not.toBeInTheDocument();
    await user.click(table.getByRole('button', { name: 'History' }));
    const history = within(screen.getByRole('region', { name: 'Subscription history' }));
    expect(await history.findByText('Saved edition unavailable')).toBeVisible();
    expect(history.queryByRole('link', { name: 'Read report' })).not.toBeInTheDocument();
    expect(history.queryByRole('link', { name: 'View progress' })).not.toBeInTheDocument();
  },
);

it('does not offer a progress link when a completed edition has lost its report reference', async () => {
  server.use(
    http.get('/api/schedules/:id/editions', () =>
      HttpResponse.json({
        items: [{ ...edition, report_id: null, version_id: null, version_number: null }],
        limit: 10,
        offset: 0,
      }),
    ),
  );
  const { user } = renderApp('/subscriptions', 'user');
  await user.click(await screen.findByRole('button', { name: 'History' }));
  const history = within(screen.getByRole('region', { name: 'Subscription history' }));
  expect(await history.findByText('Saved edition unavailable')).toBeVisible();
  expect(history.queryByRole('link')).not.toBeInTheDocument();
});
