import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { server } from '@/test/server';
import { PushSettings } from './PushSettings';

afterEach(() => vi.unstubAllGlobals());

it('explains unavailable delivery without requesting browser permission', async () => {
  vi.stubGlobal('isSecureContext', false);
  server.use(
    http.get('/api/me/notifications/push', () =>
      HttpResponse.json({ available: false, public_key: null, devices: [] }),
    ),
  );
  render(<PushSettings />);
  expect(
    await screen.findByText('Browser push has not been configured for this installation.'),
  ).toBeVisible();
  expect(screen.getByRole('button', { name: 'Enable push on this browser' })).toBeDisabled();
  expect(screen.getByText(/add this app to the Home Screen/)).toBeVisible();
});

it('removes a subscribed device even from an unsupported browser', async () => {
  vi.stubGlobal('isSecureContext', false);
  let removed = false;
  server.use(
    http.get('/api/me/notifications/push', () =>
      HttpResponse.json({
        available: true,
        public_key: 'key',
        devices: removed
          ? []
          : [{ id: 'device', endpoint_hash: 'hash', created_at: '2026-09-01T12:00:00Z' }],
      }),
    ),
    http.delete('/api/me/notifications/push/device', () => {
      removed = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(<PushSettings />);
  await user.click(await screen.findByRole('button', { name: 'Remove browser 1' }));
  expect(await screen.findByText('No browsers are subscribed.')).toBeVisible();
  expect(removed).toBe(true);
});
