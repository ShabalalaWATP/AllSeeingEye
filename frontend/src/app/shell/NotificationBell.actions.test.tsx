import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { Bell } from '@/lib/api/bell';
import { signalBellChanged } from '@/lib/bellSignal';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellAlert, bellAlerts, bellSummary, noPreferences } from '@/test/fixtures.bell';
import { reportJob } from '@/test/reportJobFixture';
import { installDialogStub } from '@/test/dialogStub';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';

const REPORT = '11111111-1111-4111-8111-111111111111';
const failure = (status = 500, message = 'Down.') =>
  HttpResponse.json({ error: { code: 'boom', message } }, { status });

function serve(bell: Bell, jobs = { items: [] as unknown[] }) {
  server.use(
    http.get('/api/bell', () => HttpResponse.json(bell)),
    http.get('/api/report-jobs', () => HttpResponse.json(jobs)),
  );
}

async function openBell(name: string | RegExp) {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }], {
    initialEntries: ['/research/saved'],
  });
  const user = userEvent.setup();
  render(<RouterProvider router={router} />);
  const bell = await screen.findByRole('button', { name });
  await user.click(bell);
  return { user, router, bell, panel: screen.getByRole('dialog', { name: 'Notifications' }) };
}

const destination = (overrides: Record<string, unknown>) =>
  HttpResponse.json({
    kind: 'alerts',
    available: true,
    report_id: null,
    monitor_id: null,
    transition_id: null,
    message: null,
    ...overrides,
  });

describe('notification bell actions', () => {
  installDialogStub();

  it('opens the authorised destination, or explains why it cannot', async () => {
    serve(bellSummary(bellAlerts(3)));
    server.use(
      http.get('/api/bell/alerts/:id/destination', ({ params }) => {
        if (params.id === bellAlerts(3)[0]?.id)
          return destination({ kind: 'report', report_id: REPORT });
        if (params.id === bellAlerts(3)[1]?.id)
          return destination({
            kind: 'report',
            available: false,
            message: 'The report made for this alert is no longer available to your account.',
          });
        return failure(404, 'Alert not found.');
      }),
    );
    const { user, router, panel } = await openBell('Notifications, 3 unread');
    await user.click(within(panel).getByRole('button', { name: /^Alert 2/ }));
    expect(await within(panel).findByText(/report made for this alert/)).toBeVisible();
    expect(within(panel).getByRole('link', { name: 'Open Alerts' })).toHaveAttribute(
      'href',
      '/warning',
    );
    await user.click(within(panel).getByRole('button', { name: /^Alert 3/ }));
    expect(await within(panel).findByText(/no longer available to your account/)).toBeVisible();
    await user.click(within(panel).getByRole('button', { name: /^Alert 1/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe(`/reports/${REPORT}`));
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
  });

  it('acknowledges in place once, and a failure leaves the item and count unchanged', async () => {
    let requests = 0;
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    serve(bellSummary(bellAlerts(2)));
    server.use(
      http.post('/api/bell/alerts/acknowledge', async ({ request }) => {
        requests += 1;
        await gate;
        const body = (await request.json()) as { alert_ids: string[] };
        return HttpResponse.json({ acknowledged: body.alert_ids, failed: [] });
      }),
    );
    const { user, bell, panel } = await openBell('Notifications, 2 unread');
    const acknowledge = within(panel).getByRole('button', { name: 'Acknowledge Alert 1' });
    await user.click(acknowledge);
    await user.click(acknowledge);
    expect(acknowledge).toHaveAttribute('aria-disabled', 'true');
    serve(bellSummary(bellAlerts(2).slice(1)));
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, 1 unread'));
    expect(requests).toBe(1);
    expect(within(panel).queryByRole('button', { name: /^Alert 1/ })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(within(panel).getByRole('heading', { name: /Alerts to review/ })).toHaveFocus(),
    );

    server.use(http.post('/api/bell/alerts/acknowledge', () => failure()));
    await user.click(within(panel).getByRole('button', { name: 'Acknowledge Alert 2' }));
    expect(await within(panel).findByText('Not acknowledged. Down. Try again.')).toBeVisible();
    expect(within(panel).getByRole('button', { name: /^Alert 2/ })).toBeVisible();
    expect(bell).toHaveAccessibleName('Notifications, 1 unread');
  });

  it('acknowledges only the eligible alerts shown, after explaining the scope', async () => {
    const [personal, team, archived] = bellAlerts(3);
    const items = [
      personal!,
      { ...team!, team_id: '33333333-3333-4333-8333-333333333333', team_name: 'Desk' },
      { ...archived!, can_acknowledge: false },
    ];
    serve(bellSummary(items, { total: 9 }));
    const sent: string[][] = [];
    server.use(
      http.post('/api/bell/alerts/acknowledge', async ({ request }) => {
        const body = (await request.json()) as { alert_ids: string[] };
        sent.push(body.alert_ids);
        return HttpResponse.json({
          acknowledged: [personal!.id],
          failed: [{ alert_id: team!.id, message: 'Archived teams are read-only.' }],
        });
      }),
    );
    const { user, panel } = await openBell('Notifications, 9 unread');
    expect(within(panel).getByText(/Read-only/)).toBeVisible();
    await user.click(within(panel).getByRole('button', { name: 'Acknowledge 2 shown' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Acknowledge 2 shown alerts?' });
    expect(within(dialog).getByText('Alert 1')).toBeVisible();
    expect(within(dialog).queryByText('Alert 3')).not.toBeInTheDocument();
    expect(dialog).toHaveTextContent(/clears it for everyone in that team/);
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(sent).toEqual([]);
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeInTheDocument();

    await user.click(within(panel).getByRole('button', { name: 'Acknowledge 2 shown' }));
    await user.click(screen.getByRole('button', { name: 'Acknowledge shown' }));
    await waitFor(() => expect(sent).toEqual([[personal!.id, team!.id]]));
    expect(
      await within(panel).findByText(
        '1 not acknowledged and still listed: Alert 2 (Archived teams are read-only.)',
      ),
    ).toBeVisible();
  });

  it('mutes a rule for this account with an undo, and saves kind settings', async () => {
    const rule = bellAlert.indicator_id!;
    serve(bellSummary([bellAlert]));
    let unmuted = 0;
    server.use(
      http.put('/api/bell/muted-rules/:id', () =>
        HttpResponse.json({
          muted_kinds: [],
          muted_rules: [{ indicator_id: rule, name: 'Kharkiv strikes', muted_at: 'x' }],
        }),
      ),
      http.delete('/api/bell/muted-rules/:id', () => {
        unmuted += 1;
        return HttpResponse.json(noPreferences);
      }),
    );
    const { user, panel } = await openBell('Notifications, 1 unread');
    serve(bellSummary([]));
    await user.click(within(panel).getByRole('button', { name: /^Mute this rule/ }));
    expect(await within(panel).findByText(/The rule still runs/)).toBeVisible();
    await user.click(within(panel).getByRole('button', { name: 'Undo mute' }));
    await waitFor(() => expect(unmuted).toBe(1));

    await user.click(within(panel).getByRole('button', { name: 'Settings' }));
    const alerts = within(panel).getByRole('checkbox', { name: /^Alerts/ });
    expect(alerts).toBeChecked();
    server.use(http.put('/api/bell/preferences', () => failure()));
    await user.click(alerts);
    expect(await within(panel).findByRole('alert')).toHaveTextContent(/previous setting/);
    expect(alerts).toBeChecked();
    let saved: unknown = null;
    server.use(
      http.put('/api/bell/preferences', async ({ request }) => {
        saved = await request.json();
        return HttpResponse.json({ ...noPreferences, muted_kinds: ['alerts'] });
      }),
      http.get('/api/bell', () =>
        HttpResponse.json(
          bellSummary([], {
            muted: true,
            preferences: { ...noPreferences, muted_kinds: ['alerts'] },
          }),
        ),
      ),
    );
    await user.click(alerts);
    await waitFor(() => expect(saved).toEqual({ muted_kinds: ['alerts'] }));
    await waitFor(() => expect(alerts).not.toBeChecked());
  });

  it('reconciles a change from another session and leaves muted kinds out of the count', async () => {
    const jobs = {
      items: [
        reportJob({ status: 'completed', updated_at: new Date(Date.now() + 60_000).toISOString() }),
      ],
    };
    serve(bellSummary(bellAlerts(2)), jobs);
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }]);
    render(<RouterProvider router={router} />);
    const bell = await screen.findByRole('button', { name: 'Notifications, 3 unread' });
    const muted = {
      ...noPreferences,
      muted_kinds: ['alerts', 'research'] as Bell['preferences']['muted_kinds'],
    };
    serve(bellSummary(bellAlerts(2), { muted: true, preferences: muted }), jobs);
    act(() => signalBellChanged());
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, nothing unread'));
  });
});
