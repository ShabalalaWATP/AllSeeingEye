import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';

import { server } from '@/test/server';
import { EmailNotificationSettings } from './EmailNotificationSettings';

it('discloses unavailable SMTP and saves account and separate attention opt-ins', async () => {
  const saved: unknown[] = [];
  server.use(
    http.get('/api/me/notifications/email', () =>
      HttpResponse.json({
        enabled: false,
        include_names: false,
        confirmed: true,
        available: false,
        destination: 'user@example.invalid',
      }),
    ),
    http.get('/api/schedules/example/notifications/email', () =>
      HttpResponse.json({ policy: 'none', attention: false }),
    ),
    http.put('/api/me/notifications/email', async ({ request }) => {
      saved.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
    http.put('/api/schedules/example/notifications/email', async ({ request }) => {
      saved.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={['/account?subscription=example']}>
      <EmailNotificationSettings />
    </MemoryRouter>,
  );
  expect(await screen.findByText(/Email is not configured/)).toBeVisible();
  await user.click(screen.getByLabelText('Allow subscription emails to my account address'));
  await user.selectOptions(screen.getByLabelText('Edition emails'), 'material_changes');
  await user.click(screen.getByLabelText('Notify me when this subscription needs attention'));
  await user.click(screen.getByRole('button', { name: 'Save email preferences' }));
  expect(await screen.findByText(/Email preferences saved/)).toBeVisible();
  expect(saved).toEqual([
    { enabled: true, include_names: false },
    { policy: 'material_changes', attention: true },
  ]);
});
