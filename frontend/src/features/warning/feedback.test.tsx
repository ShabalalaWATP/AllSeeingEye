import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { eyeAnswer } from '@/components/assistant/assistantFixture';
import { alert, indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('submits an optional disposition and displays the retained shared decision', async () => {
  let submitted: unknown;
  server.use(
    http.post('/api/warning/alerts/:id/ack', async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json({
        ...alert,
        acknowledged_at: '2026-09-05T12:00:00Z',
        disposition: 'noise',
        disposition_note: 'Duplicate coverage',
      });
    }),
  );
  const { user } = renderApp('/warning', 'user');
  const list = await screen.findByRole('list', { name: 'Alerts' });
  const item = within(list).getAllByRole('listitem')[0]!;
  await user.selectOptions(within(item).getByLabelText('Disposition (optional)'), 'noise');
  await user.type(within(item).getByLabelText('Note (optional)'), 'Duplicate coverage');
  await user.click(within(item).getByRole('button', { name: 'Acknowledge' }));
  await waitFor(() =>
    expect(submitted).toEqual({ disposition: 'noise', note: 'Duplicate coverage' }),
  );
  expect(await within(item).findByText(/Shared first acknowledgement is retained/)).toBeVisible();
  expect(within(item).queryByLabelText('Disposition (optional)')).not.toBeInTheDocument();
});

it('shows the known 30-day feedback split after opening the rule', async () => {
  server.use(
    http.get('/api/warning/indicators/:id/feedback', () =>
      HttpResponse.json({
        indicator_id: indicator.id,
        since: '2026-08-08T00:00:00Z',
        until: '2026-09-07T00:00:00Z',
        useful: 7,
        noise: 3,
        duplicate: 2,
        time_basis: 'UTC acknowledgement day; today and the previous 29 days',
      }),
    ),
  );
  const { user } = renderApp('/warning', 'user');
  await user.click(await screen.findByText('Recent feedback'));
  expect(await screen.findByText('Useful 7 · Noise 3 · Duplicate 2')).toBeVisible();
  expect(screen.getByText(/30-day window: UTC acknowledgement day/)).toBeVisible();
});

it('asks only the selected alert and explains the sample counts', async () => {
  let submitted: unknown;
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json({
        ...eyeAnswer,
        continuation_id: null,
        scope: { mode: 'alert', bbox: null, selected: null },
        alert: {
          id: alert.id,
          matched_count: 300,
          stored_sample_size: 20,
          available_evidence_count: 1,
        },
      });
    }),
  );
  const { user } = renderApp('/warning', 'user');
  await user.click((await screen.findAllByRole('button', { name: 'Explain with Ask Eye' }))[0]!);
  expect(await screen.findByText('Alert: currently retained referenced evidence')).toBeVisible();
  expect(submitted).toEqual({
    scope: 'alert',
    alert_id: alert.id,
    question: 'Explain the available evidence for this alert and its gaps.',
  });
  expect(
    screen.getByText(/300 matched at firing; 20 stored references; 1 available/),
  ).toBeInTheDocument();
});

it('creates an hourly ratio rule with an explicit warm-up explanation', async () => {
  let submitted: unknown;
  server.use(
    http.post('/api/warning/indicators', async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json(indicator, { status: 201 });
    }),
  );
  const { user } = renderApp('/warning', 'user');
  const form = await screen.findByRole('form', { name: 'New indicator' });
  await user.type(within(form).getByLabelText('Indicator name'), 'Unusual activity');
  await user.type(within(form).getByLabelText('Ratio to hourly mean (optional)'), '2');
  expect(within(form).getByLabelText('Window')).toBeDisabled();
  expect(within(form).getByText(/Requires at least seven days and 168 hours/)).toBeVisible();
  await user.click(within(form).getByRole('button', { name: 'Add indicator' }));
  await waitFor(() =>
    expect(submitted).toMatchObject({ baseline_ratio: 2, baseline_days: 30, window_minutes: 60 }),
  );
});
