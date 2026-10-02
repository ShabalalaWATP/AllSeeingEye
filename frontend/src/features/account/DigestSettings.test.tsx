import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { server } from '@/test/server';
import { DigestSettings } from './DigestSettings';

it('keeps delivery off until opted in and saves the chosen local schedule', async () => {
  const saved: unknown[] = [];
  server.use(
    http.get('/api/me/notifications/digest', () =>
      HttpResponse.json({ enabled: false, timezone: 'UTC', hour: 8 }),
    ),
    http.put('/api/me/notifications/digest', async ({ request }) => {
      saved.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(<DigestSettings />);
  const enabled = await screen.findByLabelText('Send a daily digest');
  expect(enabled).not.toBeChecked();
  await user.click(enabled);
  const zone = screen.getByLabelText(/Time zone/);
  await user.clear(zone);
  await user.type(zone, 'Europe/London');
  const hour = screen.getByLabelText('Local hour (0 to 23)');
  await user.clear(hour);
  await user.type(hour, '17');
  await user.click(screen.getByRole('button', { name: 'Save digest settings' }));
  expect(await screen.findByText('Daily digest settings saved.')).toBeVisible();
  expect(saved).toEqual([{ enabled: true, timezone: 'Europe/London', hour: 17 }]);
});

it('shows an actionable save failure', async () => {
  server.use(
    http.get('/api/me/notifications/digest', () =>
      HttpResponse.json({ enabled: false, timezone: 'UTC', hour: 8 }),
    ),
    http.put('/api/me/notifications/digest', () => new HttpResponse(null, { status: 422 })),
  );
  const user = userEvent.setup();
  render(<DigestSettings />);
  await user.click(await screen.findByRole('button', { name: 'Save digest settings' }));
  expect(await screen.findByText(/Check the time zone/)).toBeVisible();
});

it('reports an unavailable preference service without offering a save action', async () => {
  server.use(
    http.get('/api/me/notifications/digest', () => new HttpResponse(null, { status: 503 })),
  );
  render(<DigestSettings />);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Daily digest settings could not be loaded',
  );
  expect(screen.queryByRole('button', { name: 'Save digest settings' })).not.toBeInTheDocument();
});
