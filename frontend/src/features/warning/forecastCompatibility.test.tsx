import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { Indicator } from '@/lib/api/warning';
import { alert, indicator, plainUser } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

it('retains feedback through the other-owner confirmation and never sends it on cancellation', async () => {
  const requests: unknown[] = [];
  const foreign = { ...alert, created_by: plainUser.id, owner_name: plainUser.display_name };
  server.use(
    http.get('/api/warning/alerts', ({ request }) => {
      const items = new URL(request.url).searchParams.get('scope') === 'all' ? [foreign] : [];
      return HttpResponse.json({ items, unacknowledged: items.length });
    }),
    http.post('/api/warning/alerts/:id/ack', async ({ request }) => {
      requests.push(await request.json());
      return HttpResponse.json({
        ...foreign,
        owner_name: null,
        acknowledged_at: '2026-09-05T12:00:00Z',
        disposition: 'noise',
        disposition_note: 'Already covered',
      });
    }),
  );
  const { user } = renderApp('/warning?scope=all', 'admin');
  const list = await screen.findByRole('list', { name: 'Alerts' });
  const row = within(list).getAllByRole('listitem')[0]!;
  await user.selectOptions(within(row).getByLabelText('Disposition (optional)'), 'noise');
  await user.type(within(row).getByLabelText('Note (optional)'), 'Already covered');
  await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
  const dialog = await screen.findByRole('alertdialog');
  expect(dialog).toHaveTextContent(plainUser.display_name);
  await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
  expect(requests).toEqual([]);
  await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
  await user.click(
    within(await screen.findByRole('alertdialog')).getByRole('button', {
      name: 'Acknowledge for everyone',
    }),
  );
  await waitFor(() =>
    expect(requests).toEqual([{ disposition: 'noise', note: 'Already covered' }]),
  );
  expect(await within(row).findByText('acknowledged')).toBeVisible();
  expect(within(row).getByText(`Personal: ${plainUser.display_name}`)).toBeVisible();
  expect(within(row).getByText(/Already covered/)).toBeVisible();
});

it('preserves an edited ratio rule through pause and resume using each fresh revision', async () => {
  let saved: Indicator = {
    ...indicator,
    baseline_ratio: 2.5,
    baseline_days: 14,
    window_minutes: 60,
  };
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/warning/indicators', () => HttpResponse.json({ items: [saved] })),
    http.get('/api/warning/indicators/:id/baseline', () =>
      HttpResponse.json({
        sample_hours: 0,
        mean: null,
        earliest: null,
        as_of: '2026-09-05T12:00:00Z',
        ready: false,
        reason: 'Collecting baseline samples.',
      }),
    ),
    http.put('/api/warning/indicators/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      const { expected_updated_at: _, confirm_wider_scope: __, ...changes } = body;
      saved = { ...saved, ...changes, updated_at: `2026-09-05T12:00:0${bodies.length}Z` };
      return HttpResponse.json(saved);
    }),
  );
  const originalRevision = saved.updated_at;
  const { user } = renderApp('/warning', 'user');
  await user.click(await screen.findByRole('button', { name: `Edit ${saved.name}` }));
  const form = within(await screen.findByRole('form', { name: `Edit alert rule ${saved.name}` }));
  expect(form.getByLabelText('Ratio to hourly mean (optional)')).toHaveValue(2.5);
  expect(form.getByLabelText('Baseline window (days)')).toHaveValue(14);
  expect(form.getByLabelText('Window')).toBeDisabled();
  await user.clear(form.getByLabelText('Alert rule name'));
  await user.type(form.getByLabelText('Alert rule name'), 'Renamed ratio');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await screen.findByText('Changes to “Renamed ratio” saved.');
  await user.click(await screen.findByRole('button', { name: 'Pause Renamed ratio' }));
  await user.click(await screen.findByRole('button', { name: 'Resume Renamed ratio' }));
  await waitFor(() => expect(bodies).toHaveLength(3));
  expect(bodies.map((body) => body.enabled)).toEqual([true, false, true]);
  expect(bodies.map((body) => body.expected_updated_at)).toEqual([
    originalRevision,
    '2026-09-05T12:00:01Z',
    '2026-09-05T12:00:02Z',
  ]);
  for (const body of bodies)
    expect(body).toMatchObject({
      baseline_ratio: 2.5,
      baseline_days: 14,
      window_minutes: 60,
    });
  expect(await screen.findByText(/2.5 times the 14-day hourly mean/)).toBeVisible();
});
