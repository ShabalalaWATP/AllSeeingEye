/** KAN-208: editing or copying a non-UTC subscription keeps its local run time. */
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const london = {
  ...schedule,
  hour_utc: 7,
  timezone: 'Europe/London',
  local_hour: 8,
  local_minute: 30,
};

it.each([
  ['Edit', 'Edit subscription', 'Save changes'],
  ['Duplicate', 'Duplicate subscription', 'Create copy'],
])('%s starts from the local hour and sends it back unchanged', async (action, title, save) => {
  let sent: Record<string, unknown> | null = null;
  const capture = async ({ request }: { request: Request }) => {
    sent = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...london, ...sent });
  };
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [london] })),
    http.put('/api/schedules/:id', capture),
    http.post('/api/schedules', capture),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: action }));
  const form = within(await screen.findByRole('form', { name: title }));
  const hour = form.getByLabelText('Hour');
  expect(hour).toHaveValue('8');
  expect(within(hour).getByRole('option', { selected: true })).toHaveTextContent(
    '08:30 Europe/London',
  );
  await user.click(form.getByRole('button', { name: save }));
  await waitFor(() =>
    expect(sent).toMatchObject({ timezone: 'Europe/London', local_hour: 8, local_minute: 30 }),
  );
});

it('keeps UTC labels for a subscription without a local timezone', async () => {
  server.use(http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })));
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  const hour = form.getByLabelText('Hour');
  expect(hour).toHaveValue('6');
  expect(within(hour).getByRole('option', { selected: true })).toHaveTextContent('06:00 UTC');
});
