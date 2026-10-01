import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { Bell } from '@/lib/api/bell';
import type { ReportJob } from '@/lib/api/reportJobs';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { bellAlerts, bellSummary } from '@/test/fixtures.bell';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';
import { seenKey } from './notificationSeen';

const SEEN = Date.parse('2026-09-11T09:00:00Z');
const failure = () =>
  HttpResponse.json({ error: { code: 'boom', message: 'Down.' } }, { status: 500 });

function job(id: string, overrides: Partial<ReportJob>): ReportJob {
  return reportJob({ id, ...overrides });
}

const finishedJobs = [
  job('a1111111-2222-4333-8444-555555555555', {
    title: 'Port activity assessment',
    status: 'completed',
    report_id: '11111111-1111-4111-8111-111111111111',
    updated_at: '2026-09-11T10:00:00Z',
  }),
  job('b1111111-2222-4333-8444-555555555555', {
    title: 'Border crossings',
    status: 'failed',
    report_id: null,
    updated_at: '2026-09-11T10:05:00Z',
  }),
  job('c1111111-2222-4333-8444-555555555555', {
    title: 'Older finished run',
    status: 'needs_review',
    updated_at: '2026-09-10T10:00:00Z',
  }),
  job('d1111111-2222-4333-8444-555555555555', { title: 'Still running', status: 'running' }),
];

function serve(bell: Bell | 'fail', jobs: { items: ReportJob[] } | 'fail') {
  server.use(
    http.get('/api/bell', () => (bell === 'fail' ? failure() : HttpResponse.json(bell))),
    http.get('/api/report-jobs', () => (jobs === 'fail' ? failure() : HttpResponse.json(jobs))),
  );
}

function renderBell(session: 'user' | 'none' = 'user') {
  if (session === 'user') useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }], {
    initialEntries: ['/research/saved'],
  });
  const user = userEvent.setup();
  return { ...render(<RouterProvider router={router} />), router, user };
}

describe('notification bell', () => {
  it('announces loading and then the empty state without inventing a count', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/bell', async () => {
        await gate;
        return HttpResponse.json(bellSummary([]));
      }),
      http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })),
    );
    const { user } = renderBell();
    const bell = screen.getByRole('button', { name: 'Notifications' });
    expect(bell).toHaveAttribute('aria-expanded', 'false');
    await user.click(bell);
    expect(bell).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Checking for notifications…')).toBeVisible();
    await act(async () => {
      release();
      await gate;
    });
    expect(await screen.findByText(/You are up to date/)).toBeVisible();
    expect(bell).toHaveAccessibleName('Notifications, nothing unread');
  });

  it('counts unacknowledged alerts and research finished since the bell was last opened', async () => {
    localStorage.setItem(seenKey(plainUser.id), String(SEEN));
    serve(bellSummary(), { items: finishedJobs });
    const { user, router } = renderBell();
    const bell = await screen.findByRole('button', { name: 'Notifications, 3 unread' });
    expect(within(bell).getByText('3')).toBeInTheDocument();
    expect(screen.getByText('3 unread notifications')).toBeInTheDocument();

    await user.click(bell);
    const panel = screen.getByRole('dialog', { name: 'Notifications' });
    expect(panel).toHaveFocus();
    const alerts = within(panel).getByRole('region', { name: 'Alerts to review · last 7 days' });
    expect(within(alerts).getByRole('button', { name: /^Kharkiv strikes: 3 items/ })).toBeVisible();
    expect(within(alerts).getByText(/not listed here, whether or not/)).toBeVisible();
    expect(bell).toHaveAccessibleDescription(/alerts from the last 7 days/);
    const research = within(panel).getByRole('region', { name: 'Finished research' });
    const links = within(research).getAllByRole('link');
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/research/jobs/b1111111-2222-4333-8444-555555555555',
      '/reports/11111111-1111-4111-8111-111111111111',
      '/research/jobs/c1111111-2222-4333-8444-555555555555',
    ]);
    expect(links[0]).toHaveTextContent(/Border crossings.*New.*Stopped with an error/);
    expect(links[1]).toHaveTextContent(/Port activity assessment.*New.*Report ready/);
    expect(links[2]).toHaveTextContent(/Older finished run.*Report needs review/);
    expect(links[2]).not.toHaveTextContent('New');
    expect(within(research).queryByText('Still running')).not.toBeInTheDocument();

    // Opening marks everything seen; only the unacknowledged alert still counts.
    expect(Number(localStorage.getItem(seenKey(plainUser.id)))).toBeGreaterThan(SEEN);
    expect(bell).toHaveAccessibleName('Notifications, 1 unread');

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
    expect(bell).toHaveFocus();
    expect(bell).toHaveAttribute('aria-expanded', 'false');

    await user.click(bell);
    expect(screen.queryByText('New')).not.toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /Port activity assessment/ }));
    expect(router.state.location.pathname).toBe('/reports/11111111-1111-4111-8111-111111111111');
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
  });

  it('starts the clock on first use so older finished research is not counted', async () => {
    serve(bellSummary([]), { items: finishedJobs });
    renderBell();
    expect(
      await screen.findByRole('button', { name: 'Notifications, nothing unread' }),
    ).toBeInTheDocument();
    expect(localStorage.getItem(seenKey(plainUser.id))).not.toBeNull();
  });

  it('shows a load failure with a retry, and a partial failure beside what did load', async () => {
    serve('fail', 'fail');
    const { user } = renderBell();
    const bell = await screen.findByRole('button', {
      name: 'Notifications, could not be checked',
    });
    await user.click(bell);
    const panel = screen.getByRole('dialog', { name: 'Notifications' });
    expect(await within(panel).findByRole('alert')).toHaveTextContent(
      'Notifications could not be loaded.',
    );
    serve(bellSummary(), 'fail');
    await user.click(within(panel).getByRole('button', { name: 'Try again' }));
    expect(await within(panel).findByText('Research progress could not be loaded.')).toBeVisible();
    expect(within(panel).getByRole('button', { name: /^Kharkiv strikes/ })).toBeVisible();
    serve(bellSummary(), { items: [] });
    await user.click(within(panel).getByRole('button', { name: 'Try again' }));
    await waitFor(() => {
      expect(within(panel).queryByText('Research progress could not be loaded.')).toBeNull();
    });
  });

  it('retries only the source that failed', async () => {
    let jobRequests = 0;
    const undated = job('e1111111-2222-4333-8444-555555555555', {
      title: 'Undated run',
      status: 'completed',
      updated_at: 'not a date',
    });
    server.use(
      http.get('/api/bell', failure),
      http.get('/api/report-jobs', () => {
        jobRequests += 1;
        return HttpResponse.json({ items: [undated] });
      }),
    );
    const { user } = renderBell();
    await user.click(
      await screen.findByRole('button', { name: 'Notifications, could not be checked' }),
    );
    const panel = screen.getByRole('dialog', { name: 'Notifications' });
    expect(within(panel).getByText('Alerts could not be loaded.')).toBeVisible();
    expect(within(panel).getByRole('link', { name: /Undated run/ })).not.toHaveTextContent('New');
    serve(bellSummary(), { items: [undated] });
    await user.click(within(panel).getByRole('button', { name: 'Try again' }));
    expect(await within(panel).findByRole('button', { name: /^Kharkiv strikes/ })).toBeVisible();
    expect(jobRequests).toBe(1);
  });

  it('lists the newest alerts from the server and points to the rest on the alerts page', async () => {
    serve(bellSummary(bellAlerts(5), { total: 6 }), { items: [] });
    const { user } = renderBell();
    await user.click(await screen.findByRole('button', { name: 'Notifications, 6 unread' }));
    const alerts = screen.getByRole('list', { name: 'Unacknowledged alerts' });
    expect(
      within(alerts)
        .getAllByRole('button', { name: /^Alert \d/ })
        .map((button) => button.textContent),
    ).toEqual([1, 2, 3, 4, 5].map((n) => expect.stringContaining(`Alert ${String(n)}`) as string));
    expect(screen.getByText('1 more in the last 7 days on the Alerts page.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'All alerts' })).toHaveAttribute('href', '/warning');
    expect(screen.getByRole('link', { name: 'Research progress' })).toHaveAttribute(
      'href',
      '/research/jobs',
    );
  });

  it('closes when the pointer or focus moves elsewhere', async () => {
    serve(bellSummary(), { items: [] });
    const outside = document.createElement('button');
    document.body.append(outside);
    const { user } = renderBell();
    const bell = await screen.findByRole('button', { name: 'Notifications, 1 unread' });
    await user.click(bell);
    fireEvent.pointerDown(screen.getByRole('button', { name: /^Kharkiv/ }));
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeInTheDocument();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
    await user.click(bell);
    act(() => outside.focus());
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
    await user.click(bell);
    await user.keyboard('{a}');
    expect(screen.getByRole('dialog', { name: 'Notifications' })).toBeInTheDocument();
    await user.click(bell);
    expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument();
    outside.remove();
  });

  it('asks for nothing while signed out and starts afresh for another account', async () => {
    let requests = 0;
    server.use(
      http.get('/api/bell', () => {
        requests += 1;
        return HttpResponse.json(bellSummary());
      }),
    );
    renderBell('none');
    expect(screen.queryByRole('button', { name: /Notifications/ })).not.toBeInTheDocument();
    expect(requests).toBe(0);
    act(() => useAuthStore.getState().setSession(tokenFor(adminUser)));
    expect(await screen.findByRole('button', { name: 'Notifications, 1 unread' })).toBeVisible();
    expect(localStorage.getItem(seenKey(adminUser.id))).not.toBeNull();
    expect(localStorage.getItem(seenKey(plainUser.id))).toBeNull();
  });
});
