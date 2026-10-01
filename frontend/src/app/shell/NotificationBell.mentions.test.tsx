import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { Bell } from '@/lib/api/bell';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { bellMention, bellSummary, noPreferences } from '@/test/fixtures.bell';
import { server } from '@/test/server';

import { NotificationBell } from './NotificationBell';

const second = { ...bellMention, post_id: 'a2a2a2a2-a2a2-4a2a-8a2a-a2a2a2a2a2a2' };

function serve(bell: Bell) {
  server.use(
    http.get('/api/bell', () => HttpResponse.json(bell)),
    http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })),
  );
}

const withMentions = (items = [bellMention, second], unread = items.length) =>
  bellSummary([], { mentions: { items, unread, muted: false } });

async function openBell(name: string) {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([{ path: '*', element: <NotificationBell /> }]);
  const user = userEvent.setup();
  render(<RouterProvider router={router} />);
  const bell = await screen.findByRole('button', { name });
  await user.click(bell);
  return { user, router, bell, panel: screen.getByRole('dialog', { name: 'Notifications' }) };
}

describe('notification bell mentions', () => {
  it('counts unread mentions, shows plain-text snippets and opens the checked thread', async () => {
    serve(withMentions());
    server.use(
      http.post('/api/bell/mentions/:id/open', () =>
        HttpResponse.json({
          team_id: bellMention.team_id,
          post_id: bellMention.post_id,
          thread_id: bellMention.thread_id,
        }),
      ),
    );
    const { user, router, panel } = await openBell('Notifications, 2 unread');
    const list = within(panel).getByRole('list', { name: 'Unread mentions' });
    // Markup in a post is text, never rendered.
    expect(within(list).getAllByText(/can you check the <b>rail<\/b> yard\?/)).toHaveLength(2);
    expect(list.querySelector('b')).toBeNull();
    await user.click(
      within(list).getAllByRole('button', { name: /Lead mentioned you in Desk/ })[0]!,
    );
    await waitFor(() => expect(router.state.location.pathname).toBe('/teams'));
    const params = new URLSearchParams(router.state.location.search);
    expect(params.get('team')).toBe(bellMention.team_id);
    expect(params.get('post')).toBe(bellMention.thread_id);
  });

  it('explains a mention that is no longer available and marks shown mentions read', async () => {
    serve(withMentions());
    let marked: unknown = null;
    server.use(
      http.post('/api/bell/mentions/:id/open', () =>
        HttpResponse.json(
          { error: { code: 'not_found', message: 'This mention is no longer available.' } },
          { status: 404 },
        ),
      ),
      http.post('/api/bell/mentions/read', async ({ request }) => {
        marked = await request.json();
        return HttpResponse.json({ unread: 0 });
      }),
    );
    const { user, bell, panel } = await openBell('Notifications, 2 unread');
    await user.click(
      within(panel).getAllByRole('button', { name: /Lead mentioned you in Desk/ })[0]!,
    );
    expect(await within(panel).findByText(/no longer be in that team/)).toBeVisible();
    serve(bellSummary([]));
    await user.click(within(panel).getByRole('button', { name: 'Mark shown mentions as read' }));
    await waitFor(() =>
      expect(marked).toEqual({ post_ids: [bellMention.post_id, second.post_id] }),
    );
    await waitFor(() => expect(bell).toHaveAccessibleName('Notifications, nothing unread'));
  });

  it('leaves muted mentions out of the badge', async () => {
    serve(
      bellSummary([], {
        mentions: { items: [bellMention], unread: 1, muted: true },
        preferences: { ...noPreferences, muted_kinds: ['mentions'] },
      }),
    );
    const { panel } = await openBell('Notifications, nothing unread');
    expect(within(panel).queryByRole('list', { name: 'Unread mentions' })).not.toBeInTheDocument();
    expect(within(panel).getByText(/hidden by your settings/)).toBeVisible();
  });
});
