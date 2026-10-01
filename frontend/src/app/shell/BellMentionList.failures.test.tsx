import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { Bell } from '@/lib/api/bell';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellMention, bellSummary } from '@/test/fixtures.bell';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';

const second = {
  ...bellMention,
  post_id: 'a2a2a2a2-a2a2-4a2a-8a2a-a2a2a2a2a2a2',
  author_name: 'Alex',
};
const failure = () =>
  HttpResponse.json(
    { error: { code: 'unavailable', message: 'Service unavailable.' } },
    { status: 500 },
  );
const withMentions = (unread = 2): Bell =>
  bellSummary([], { mentions: { items: [bellMention, second], unread, muted: false } });

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
  const bell = await screen.findByRole('button', { name: /Notifications, .*unread/ });
  await user.click(bell);
  return { user, router, bell, panel: screen.getByRole('dialog', { name: 'Notifications' }) };
}

describe('bell mention recovery', () => {
  it.each([42, 100])(
    'explains when %i unread mentions exceed the displayed selection',
    async (unread) => {
      const { panel } = await openBell(() => withMentions(unread));
      expect(
        await within(panel).findByText(`${unread === 100 ? '100 or more' : '42'} unread in total.`),
      ).toBeVisible();
      expect(within(panel).getByRole('list', { name: 'Unread mentions' }).children).toHaveLength(2);
    },
  );

  it('keeps an unavailable request in place, suppresses overlapping opens and allows retry', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const opened: string[] = [];
    server.use(
      http.post('/api/bell/mentions/:id/open', async ({ params }) => {
        opened.push(String(params.id));
        if (opened.length === 1) {
          await gate;
          return failure();
        }
        return HttpResponse.json({
          team_id: bellMention.team_id,
          post_id: bellMention.post_id,
          thread_id: bellMention.thread_id,
        });
      }),
    );
    const { user, router, panel } = await openBell(withMentions);
    const first = await within(panel).findByRole('button', { name: /Lead mentioned you/ });
    await user.click(first);
    const other = within(panel).getByRole('button', { name: /Alex mentioned you/ });
    expect(other).toBeDisabled();
    expect(
      within(panel).getByRole('button', { name: 'Mark shown mentions as read' }),
    ).toBeDisabled();
    await user.click(other);
    await act(async () => {
      release();
      await gate;
    });
    expect(
      await within(panel).findByText('Could not open this mention. Service unavailable.'),
    ).toBeVisible();
    expect(router.state.location.pathname).toBe('/research/saved');
    expect(opened).toEqual([bellMention.post_id]);
    await user.click(first);
    await waitFor(() => expect(router.state.location.pathname).toBe('/teams'));
    expect(new URLSearchParams(router.state.location.search).get('post')).toBe(
      bellMention.thread_id,
    );
    expect(opened).toEqual([bellMention.post_id, bellMention.post_id]);
  });

  it('retries a failed mark-read request without losing mentions and keeps focus after the last row disappears', async () => {
    let summary = withMentions();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const requests: unknown[] = [];
    server.use(
      http.post('/api/bell/mentions/read', async ({ request }) => {
        requests.push(await request.json());
        if (requests.length === 1) return failure();
        await gate;
        summary = bellSummary([]);
        return HttpResponse.json({ unread: 0 });
      }),
    );
    const { user, bell, panel } = await openBell(() => summary);
    const mark = await within(panel).findByRole('button', { name: 'Mark shown mentions as read' });
    await user.click(mark);
    expect(
      await within(panel).findByText('Not marked as read. Service unavailable. Try again.'),
    ).toBeVisible();
    expect(bell).toHaveAccessibleName('Notifications, 2 unread');
    expect(within(panel).getByRole('button', { name: /Lead mentioned you/ })).toBeVisible();
    await user.click(mark);
    expect(within(panel).getByRole('button', { name: /Lead mentioned you/ })).toBeDisabled();
    expect(mark).toHaveAttribute('aria-disabled', 'true');
    await user.click(mark);
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, nothing unread'));
    expect(requests).toEqual([
      { post_ids: [bellMention.post_id, second.post_id] },
      { post_ids: [bellMention.post_id, second.post_id] },
    ]);
    expect(within(panel).queryByRole('list', { name: 'Unread mentions' })).not.toBeInTheDocument();
    await waitFor(() => expect(panel).toHaveFocus());
  });
});
