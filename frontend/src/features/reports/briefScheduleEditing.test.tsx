import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const pinned = {
  ...schedule,
  brief_id: '1b4b74c8-fca6-4e0b-8946-0e37b7a49c2c',
  brief_revision: 2,
  settings_revision: 'a'.repeat(64),
  enabled: false,
  timezone: 'Europe/London',
  local_hour: 9,
  local_minute: 30,
  cadence: 'monthly',
  monthday: 31,
};

it('edits only name and recurrence, shows pending and success, and restores focus', async () => {
  let current = pinned;
  let release: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  const writes: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.put('/api/schedules/:id/brief-settings', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      writes.push(body);
      await pending;
      current = {
        ...current,
        name: String(body.name),
        local_hour: 11,
        settings_revision: 'b'.repeat(64),
      };
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const edit = table.getByRole('button', { name: 'Edit' });
  expect(edit).toBeEnabled();
  await user.click(edit);
  const form = within(
    await screen.findByRole('form', { name: 'Edit Research Brief subscription' }),
  );
  expect(form.getByLabelText('Subscription name')).toHaveFocus();
  expect(form.queryByLabelText('Question')).not.toBeInTheDocument();
  expect(form.queryByLabelText('Future collection window')).not.toBeInTheDocument();
  expect(form.getByText(/remains paused/)).toBeVisible();
  await user.clear(form.getByLabelText('Subscription name'));
  await user.type(form.getByLabelText('Subscription name'), 'Edited brief schedule');
  await user.clear(form.getByLabelText('Local time'));
  await user.type(form.getByLabelText('Local time'), '11:30');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(writes).toHaveLength(1));
  expect(form.getByLabelText('Subscription name')).toBeDisabled();
  expect(form.getByRole('button', { name: 'Save changes' })).toHaveAttribute('aria-busy', 'true');
  expect(writes[0]).toEqual({
    expected_revision: pinned.settings_revision,
    name: 'Edited brief schedule',
    timezone: 'Europe/London',
    local_hour: 11,
    local_minute: 30,
    cadence: 'monthly',
    weekday: pinned.weekday,
    monthday: 31,
    anchor_month: pinned.anchor_month,
  });
  release?.();
  await screen.findByText('Subscription settings updated. Pinned brief and history preserved.');
  await waitFor(() => expect(edit).toHaveFocus());
  expect(
    screen.queryByRole('form', { name: 'Edit Research Brief subscription' }),
  ).not.toBeInTheDocument();
  expect(table.getByRole('button', { name: 'Resume' })).toBeEnabled();
});

it('retains edits and shows actionable stale/server errors without broad writes', async () => {
  let writes = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [pinned] })),
    http.put('/api/schedules/:id/brief-settings', () => {
      writes++;
      return HttpResponse.json(
        {
          error: {
            code: 'conflict',
            message:
              'The subscription settings changed. Reload subscriptions before editing again.',
          },
        },
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(
    await screen.findByRole('form', { name: 'Edit Research Brief subscription' }),
  );
  await user.clear(form.getByLabelText('Subscription name'));
  await user.type(form.getByLabelText('Subscription name'), 'Unsaved name');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  expect(await form.findByText(/Reload subscriptions before editing again/)).toBeVisible();
  expect(form.getByLabelText('Subscription name')).toHaveValue('Unsaved name');
  await user.click(form.getByRole('button', { name: 'Cancel' }));
  expect(writes).toBe(1);
  expect(table.getByRole('button', { name: 'Edit' })).toHaveFocus();
});
