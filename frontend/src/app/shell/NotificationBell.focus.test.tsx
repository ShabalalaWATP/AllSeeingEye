import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellAlerts, bellSummary } from '@/test/fixtures.bell';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';

it('restores focus after the delayed refresh removes alerts from a muted rule', async () => {
  const alerts = bellAlerts(2);
  const ruleId = alerts[0]!.indicator_id!;
  let muted = false;
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let entered: () => void = () => undefined;
  const refreshEntered = new Promise<void>((resolve) => {
    entered = resolve;
  });
  server.use(
    http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })),
    http.get('/api/bell', async () => {
      if (muted) {
        entered();
        await gate;
      }
      return HttpResponse.json(bellSummary(muted ? [] : alerts));
    }),
    http.put(`/api/bell/muted-rules/${ruleId}`, () => {
      muted = true;
      return HttpResponse.json({
        muted_kinds: [],
        muted_rules: [{ indicator_id: ruleId, name: 'Port rule', muted_at: '2026-10-10' }],
      });
    }),
  );
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const user = userEvent.setup();
  render(
    <RouterProvider router={createMemoryRouter([{ path: '*', element: <NotificationBell /> }])} />,
  );
  await user.click(await screen.findByRole('button', { name: 'Notifications, 2 unread' }));
  const panel = screen.getByRole('dialog', { name: 'Notifications' });
  try {
    await user.click(
      within(panel).getByRole('button', { name: 'Mute this rule in my bell: Alert 1' }),
    );
    await refreshEntered;
    const otherAlert = within(panel).getByRole('button', { name: /^Alert 2/ });
    otherAlert.focus();
    expect(otherAlert).toHaveFocus();
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() => expect(otherAlert).not.toBeInTheDocument());
    await waitFor(() =>
      expect(within(panel).getByRole('heading', { name: /Alerts to review/ })).toHaveFocus(),
    );
  } finally {
    release();
  }
});
