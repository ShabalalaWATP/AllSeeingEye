import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { AlertDestination, Bell } from '@/lib/api/bell';
import { useAuthStore } from '@/stores/auth';
import { installDialogStub } from '@/test/dialogStub';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellAlert, bellAlerts, bellSummary, noPreferences } from '@/test/fixtures.bell';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';
import { destinationHref } from './useBellAlertActions';

const failure = () =>
  HttpResponse.json({ error: { code: 'unavailable', message: 'Please retry.' } }, { status: 503 });

async function openBell(getBell: () => Bell) {
  server.use(
    http.get('/api/bell', () => HttpResponse.json(getBell())),
    http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })),
  );
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }], {
    initialEntries: ['/research/saved'],
  });
  const user = userEvent.setup();
  render(<RouterProvider router={router} />);
  const bell = await screen.findByRole('button', {
    name: `Notifications, ${String(getBell().alerts.total)} unread`,
  });
  await user.click(bell);
  return { user, router, bell, panel: screen.getByRole('dialog', { name: 'Notifications' }) };
}

const destination: AlertDestination = {
  available: true,
  kind: 'alerts',
  report_id: null,
  monitor_id: null,
  transition_id: null,
  message: null,
};

describe('bell action recovery', () => {
  installDialogStub();

  it('keeps a failed bulk confirmation available for retry with the same exact selection', async () => {
    const items = bellAlerts(2);
    let summary = bellSummary(items);
    const requests: string[][] = [];
    server.use(
      http.post('/api/bell/alerts/acknowledge', async ({ request }) => {
        const body = (await request.json()) as { alert_ids: string[] };
        requests.push(body.alert_ids);
        if (requests.length === 1) return failure();
        summary = bellSummary([]);
        return HttpResponse.json({ acknowledged: body.alert_ids, failed: [] });
      }),
    );
    const { user, bell, panel } = await openBell(() => summary);
    await user.click(within(panel).getByRole('button', { name: 'Acknowledge 2 shown' }));
    const confirmation = screen.getByRole('alertdialog');
    await user.click(within(confirmation).getByRole('button', { name: 'Acknowledge shown' }));
    expect(await within(confirmation).findByRole('alert')).toHaveTextContent('Please retry.');
    expect(bell).toHaveAccessibleName('Notifications, 2 unread');
    expect(within(panel).getByRole('button', { name: /^Alert 1/ })).toBeVisible();
    await user.click(within(confirmation).getByRole('button', { name: 'Acknowledge shown' }));
    expect(await within(panel).findByText('2 alerts acknowledged.')).toBeVisible();
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, nothing unread'));
    expect(requests).toEqual([items.map((item) => item.id), items.map((item) => item.id)]);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await user.click(within(panel).getByRole('button', { name: 'Dismiss' }));
    expect(within(panel).queryByText('2 alerts acknowledged.')).not.toBeInTheDocument();
  });

  it('keeps rejected acknowledgements listed and allows a subsequent single-alert retry', async () => {
    const [first, second] = bellAlerts(2);
    let summary = bellSummary([first!, second!]);
    let attempts = 0;
    server.use(
      http.post('/api/bell/alerts/acknowledge', () => {
        attempts += 1;
        if (attempts === 1)
          return HttpResponse.json({
            acknowledged: [],
            failed: [{ alert_id: first!.id, message: 'The team is read-only.' }],
          });
        summary = bellSummary([second!]);
        return HttpResponse.json({ acknowledged: [first!.id], failed: [] });
      }),
    );
    const { user, bell, panel } = await openBell(() => summary);
    await user.click(within(panel).getByRole('button', { name: 'Acknowledge Alert 1' }));
    expect(await within(panel).findByText(/Alert 1 \(The team is read-only\.\)/)).toBeVisible();
    expect(bell).toHaveAccessibleName('Notifications, 2 unread');
    await user.click(within(panel).getByRole('button', { name: 'Acknowledge Alert 1' }));
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, 1 unread'));
    expect(within(panel).getByRole('button', { name: /^Alert 2/ })).toBeVisible();
    await waitFor(() =>
      expect(within(panel).getByRole('heading', { name: /Alerts to review/ })).toHaveFocus(),
    );
  });

  it('recovers from a destination failure and navigates only after a successful access check', async () => {
    let requests = 0;
    server.use(
      http.get('/api/bell/alerts/:id/destination', () => {
        requests += 1;
        if (requests === 1) return failure();
        return HttpResponse.json({
          ...destination,
          kind: 'transition',
          monitor_id: bellAlert.id,
          transition_id: bellAlert.indicator_id,
        });
      }),
    );
    const { user, router, panel } = await openBell(() => bellSummary([bellAlert]));
    await user.click(
      within(panel).getByRole('button', { name: new RegExp(`^${bellAlert.title}`) }),
    );
    expect(
      await within(panel).findByText('Could not open this alert. Please retry.'),
    ).toBeVisible();
    expect(router.state.location.pathname).toBe('/research/saved');
    await user.click(
      within(panel).getByRole('button', { name: new RegExp(`^${bellAlert.title}`) }),
    );
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        `/annotation-monitors/${bellAlert.id}/transitions/${bellAlert.indicator_id!}`,
      ),
    );
  });

  it('explains an unavailable destination even when the server has no message', async () => {
    server.use(
      http.get('/api/bell/alerts/:id/destination', () =>
        HttpResponse.json({ ...destination, available: false }),
      ),
    );
    const { user, router, panel } = await openBell(() => bellSummary(bellAlerts(1)));
    await user.click(within(panel).getByRole('button', { name: /^Alert 1/ }));
    expect(await within(panel).findByText(/It may have been removed/)).toBeVisible();
    expect(router.state.location.pathname).toBe('/research/saved');
    expect(panel).toBeVisible();
  });

  it('retains an alert after a mute failure, then reports an unsuccessful undo honestly', async () => {
    const rule = bellAlert.indicator_id!;
    let summary = bellSummary([bellAlert]);
    let attempts = 0;
    server.use(
      http.put('/api/bell/muted-rules/:id', () => {
        attempts += 1;
        if (attempts === 1) return failure();
        // The rule became unavailable while this alert was displayed: no name is returned.
        summary = bellSummary([]);
        return HttpResponse.json(noPreferences);
      }),
      http.delete(`/api/bell/muted-rules/${rule}`, failure),
    );
    const { user, bell, panel } = await openBell(() => summary);
    await user.click(within(panel).getByRole('button', { name: /^Mute this rule/ }));
    expect(await within(panel).findByText('Please retry.')).toBeVisible();
    expect(bell).toHaveAccessibleName('Notifications, 1 unread');
    await user.click(within(panel).getByRole('button', { name: /^Mute this rule/ }));
    expect(await within(panel).findByText(/Alerts from this rule no longer appear/)).toBeVisible();
    await user.click(within(panel).getByRole('button', { name: 'Undo mute' }));
    expect(await within(panel).findByText('Please retry.')).toBeVisible();
    expect(within(panel).queryByText('Rule unmuted.')).not.toBeInTheDocument();
  });
});

describe('authorised bell destinations', () => {
  it.each([
    { ...destination, kind: 'report' as const },
    { ...destination, kind: 'transition' as const, monitor_id: bellAlert.id },
    { ...destination, kind: 'transition' as const, transition_id: bellAlert.id },
    { ...destination, available: false },
  ])('does not invent a destination when authorised identifiers are absent: %j', (target) => {
    expect(destinationHref(target)).toBeNull();
  });

  it('supports the Alerts page and safely encodes report identifiers', () => {
    expect(destinationHref(destination)).toBe('/warning');
    expect(destinationHref({ ...destination, kind: 'report', report_id: 'a/b?c' })).toBe(
      '/reports/a%2Fb%3Fc',
    );
  });
});
