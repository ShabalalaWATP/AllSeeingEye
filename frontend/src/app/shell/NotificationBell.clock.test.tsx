import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { ReportJob } from '@/lib/api/reportJobs';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellSummary } from '@/test/fixtures.bell';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';
import { seenKey } from './notificationSeen';

function finished(id: string, updated_at: string): ReportJob {
  return reportJob({ id, title: `Run ${id.slice(0, 1)}`, status: 'completed', updated_at });
}

function renderBell(jobs: ReportJob[]) {
  server.use(
    http.get('/api/bell', () => HttpResponse.json(bellSummary([]))),
    http.get('/api/report-jobs', () => HttpResponse.json({ items: jobs })),
  );
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }]);
  render(<RouterProvider router={router} />);
  return userEvent.setup();
}

describe('notification bell clock', () => {
  it('stamps the newest server time, so a slow client clock cannot leave the badge stuck', async () => {
    // The server's clock is far ahead of this browser's.
    const newest = '2099-01-02T10:00:00Z';
    localStorage.setItem(seenKey(plainUser.id), String(Date.parse('2099-01-01T00:00:00Z')));
    const user = renderBell([
      finished('a1111111-2222-4333-8444-555555555555', '2099-01-01T09:00:00Z'),
      finished('b1111111-2222-4333-8444-555555555555', newest),
    ]);
    const bell = await screen.findByRole('button', { name: 'Notifications, 2 unread' });
    await user.click(bell);
    expect(localStorage.getItem(seenKey(plainUser.id))).toBe(String(Date.parse(newest)));
    expect(bell).toHaveAccessibleName('Notifications, nothing unread');
    // While open, the runs that were new when it opened stay marked as new.
    const research = screen.getByRole('region', { name: 'Finished research' });
    expect(within(research).getAllByText('New')).toHaveLength(2);
  });

  it('corrects a stamp left by a fast client clock to the newest server time', async () => {
    const ahead = Date.parse('2099-06-01T00:00:00Z');
    localStorage.setItem(seenKey(plainUser.id), String(ahead));
    const user = renderBell([
      finished('c1111111-2222-4333-8444-555555555555', '2026-09-11T10:05:00Z'),
    ]);
    const bell = await screen.findByRole('button', { name: 'Notifications, nothing unread' });
    await user.click(bell);
    expect(localStorage.getItem(seenKey(plainUser.id))).toBe(
      String(Date.parse('2026-09-11T10:05:00Z')),
    );
  });

  it('leaves the stored time alone when no research has finished', async () => {
    localStorage.setItem(seenKey(plainUser.id), '1000');
    const user = renderBell([]);
    const bell = await screen.findByRole('button', { name: 'Notifications, nothing unread' });
    await user.click(bell);
    expect(localStorage.getItem(seenKey(plainUser.id))).toBe('1000');
  });
});
