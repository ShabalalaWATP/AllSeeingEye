import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { BellPreferences } from '@/lib/api/bell';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellAlert, bellSummary, noPreferences } from '@/test/fixtures.bell';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';

const failure = () =>
  HttpResponse.json({ error: { code: 'unavailable', message: 'Save failed.' } }, { status: 500 });

async function openSettings() {
  server.use(http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })));
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }]);
  const user = userEvent.setup();
  render(<RouterProvider router={router} />);
  await user.click(await screen.findByRole('button', { name: /^Notifications/ }));
  const panel = screen.getByRole('dialog', { name: 'Notifications' });
  await user.click(within(panel).getByRole('button', { name: 'Settings' }));
  return { user, panel };
}

describe('bell preference interactions', () => {
  it('shows unavailable settings without offering mutations when preferences cannot be loaded', async () => {
    server.use(http.get('/api/bell', failure));
    const { panel } = await openSettings();
    expect(
      await screen.findByRole('button', { name: 'Notifications, could not be checked' }),
    ).toBeVisible();
    expect(await within(panel).findByText('Settings are loading or unavailable.')).toBeVisible();
    expect(within(panel).queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('unhides one kind without clearing other choices and blocks concurrent preference edits', async () => {
    let preferences: BellPreferences = { ...noPreferences, muted_kinds: ['alerts', 'mentions'] };
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const requests: unknown[] = [];
    server.use(
      http.get('/api/bell', () => HttpResponse.json(bellSummary([], { preferences }))),
      http.put('/api/bell/preferences', async ({ request }) => {
        const body = (await request.json()) as { muted_kinds: BellPreferences['muted_kinds'] };
        requests.push(body);
        await gate;
        preferences = { ...preferences, muted_kinds: body.muted_kinds };
        return HttpResponse.json(preferences);
      }),
    );
    const { user, panel } = await openSettings();
    const alerts = await within(panel).findByRole('checkbox', { name: /^Alerts/ });
    const mentions = within(panel).getByRole('checkbox', { name: /^Board mentions/ });
    expect(alerts).not.toBeChecked();
    expect(mentions).not.toBeChecked();
    await user.click(alerts);
    expect(mentions).toBeDisabled();
    await user.click(mentions);
    await waitFor(() => expect(requests).toEqual([{ muted_kinds: ['mentions'] }]));
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() => expect(alerts).toBeChecked());
    expect(mentions).not.toBeChecked();
    expect(await within(panel).findByRole('status')).toHaveTextContent(
      'Alerts shown in your bell.',
    );
    await waitFor(() => expect(mentions).toBeEnabled());
  });

  it('retains a failed rule unmute for retry and preserves the other muted rule', async () => {
    const first = {
      indicator_id: bellAlert.indicator_id!,
      name: 'Strikes',
      muted_at: '2026-09-05',
    };
    const second = { ...first, indicator_id: bellAlert.id, name: 'Airspace' };
    let preferences: BellPreferences = { muted_kinds: ['research'], muted_rules: [first, second] };
    let attempts = 0;
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/bell', () => HttpResponse.json(bellSummary([], { preferences }))),
      http.delete(`/api/bell/muted-rules/${first.indicator_id}`, async () => {
        attempts += 1;
        if (attempts === 1) return failure();
        await gate;
        preferences = { ...preferences, muted_rules: [second] };
        return HttpResponse.json(preferences);
      }),
    );
    const { user, panel } = await openSettings();
    const unmute = await within(panel).findByRole('button', { name: 'Unmute Strikes' });
    await user.click(unmute);
    expect(await within(panel).findByRole('alert')).toHaveTextContent(
      'Save failed. Your previous setting is unchanged. Try again.',
    );
    expect(unmute).toBeVisible();
    await user.click(unmute);
    expect(unmute).toHaveAttribute('aria-disabled', 'true');
    expect(within(panel).getByRole('button', { name: 'Unmute Airspace' })).toBeDisabled();
    expect(within(panel).getByRole('checkbox', { name: /^Finished research/ })).toBeDisabled();
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() =>
      expect(within(panel).queryByRole('button', { name: 'Unmute Strikes' })).toBeNull(),
    );
    expect(within(panel).getByRole('button', { name: 'Unmute Airspace' })).toBeVisible();
    expect(within(panel).getByRole('checkbox', { name: /^Finished research/ })).not.toBeChecked();
    expect(within(panel).queryByRole('alert')).not.toBeInTheDocument();
    expect(within(panel).getByRole('status')).toHaveTextContent('Strikes unmuted.');
    expect(attempts).toBe(2);
  });
});
