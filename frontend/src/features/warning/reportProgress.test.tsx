import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { alert } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('shows queued report progress and a recoverable job link beside the alert', async () => {
  server.use(
    http.get('/api/warning/alerts', () =>
      HttpResponse.json({
        items: [
          {
            ...alert,
            report_id: null,
            report_job_id: 'saved-job',
            report_status: 'paused',
            report_error: 'interrupted_uncertain',
          },
        ],
        unacknowledged: 1,
      }),
    ),
  );
  renderApp('/warning', 'user');
  const list = await screen.findByRole('list', { name: 'Alerts' });
  expect(within(list).getByText(/Report paused/)).toBeVisible();
  expect(within(list).getByRole('link', { name: 'View report progress' })).toHaveAttribute(
    'href',
    '/research/jobs/saved-job',
  );
});

it('makes failed admission visible without inventing a report destination', async () => {
  server.use(
    http.get('/api/warning/alerts', () =>
      HttpResponse.json({
        items: [
          {
            ...alert,
            report_id: null,
            report_job_id: null,
            report_status: 'failed',
            report_error: 'admission_failed',
          },
        ],
        unacknowledged: 1,
      }),
    ),
  );
  renderApp('/warning', 'user');
  const list = await screen.findByRole('list', { name: 'Alerts' });
  expect(within(list).getByText(/Report could not be queued/)).toBeVisible();
  expect(
    within(list).queryByRole('link', { name: 'View report progress' }),
  ).not.toBeInTheDocument();
});
