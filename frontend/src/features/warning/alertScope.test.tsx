import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { adminUser, plainUser } from '@/test/fixtures';
import { alert } from '@/test/fixtures.warning';
import { installDialogStub } from '@/test/dialogStub';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

const desk = {
  id: '44444444-4444-4444-8444-444444444444',
  name: 'Northern desk',
  is_active: true,
  created_by: adminUser.id,
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  description: null,
};
const own = { ...alert, id: 'a0000000-0000-4000-8000-000000000001', title: 'My own alert' };
const ownAdmin = { ...own, created_by: adminUser.id, owner_name: adminUser.display_name };
const theirs = {
  ...alert,
  id: 'a0000000-0000-4000-8000-000000000002',
  title: 'Uma private alert',
  created_by: plainUser.id,
  owner_name: plainUser.display_name,
};
const deskAlert = {
  ...alert,
  id: 'a0000000-0000-4000-8000-000000000003',
  title: 'Desk alert',
  team_id: desk.id,
  created_by: plainUser.id,
  owner_name: null,
};

function stubAlerts(ack: (id: string) => Response | Promise<Response> = okAck) {
  const lists: URL[] = [];
  const acks: string[] = [];
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [desk] })),
    http.get('/api/teams/:id', () => HttpResponse.json({ team: desk, members: [] })),
    http.get('/api/warning/alerts', ({ request }) => {
      const url = new URL(request.url);
      lists.push(url);
      const items =
        url.searchParams.get('scope') === 'all' ? [ownAdmin, theirs, deskAlert] : [ownAdmin];
      return HttpResponse.json({ items, unacknowledged: items.length });
    }),
    http.post('/api/warning/alerts/:id/ack', ({ params }) => {
      acks.push(String(params.id));
      return ack(String(params.id));
    }),
  );
  return { lists, acks };
}

function okAck(id: string) {
  const row = [ownAdmin, theirs, deskAlert].find((item) => item.id === id)!;
  return HttpResponse.json({
    ...row,
    acknowledged_at: '2026-09-05T12:00:00Z',
    acknowledged_by: adminUser.id,
  });
}

/** Requests made by the alerts page itself, not the shell's last-day bell poll. */
const pageRequests = (urls: URL[]) => urls.filter((url) => !url.searchParams.has('hours'));

describe('alert ownership scope', () => {
  it('defaults administrators to their own work and widens only by explicit choice', async () => {
    const { lists } = stubAlerts();
    const { user, router } = renderApp('/warning', 'admin');
    const list = await screen.findByRole('list', { name: 'Alerts' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);
    const scope = screen.getByRole('group', { name: 'Whose alerts to show' });
    expect(within(scope).getByRole('button', { name: 'Mine and my teams' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(
      screen.getByText(/your personal alerts and alerts from your current teams/i),
    ).toBeVisible();
    expect(pageRequests(lists).every((url) => !url.searchParams.has('scope'))).toBe(true);

    await user.click(within(scope).getByRole('button', { name: 'All users' }));
    await waitFor(() => {
      expect(
        within(screen.getByRole('list', { name: 'Alerts' })).getAllByRole('listitem'),
      ).toHaveLength(3);
    });
    expect(router.state.location.search).toBe('?scope=all');
    expect(screen.getByText(/every user's personal alerts and every team's alerts/i)).toBeVisible();
    const rows = within(screen.getByRole('list', { name: 'Alerts' })).getAllByRole('listitem');
    expect(within(rows[0]!).getByText('Personal')).toBeVisible();
    expect(within(rows[1]!).getByText('Personal: Uma User')).toBeVisible();
    expect(within(rows[2]!).getByText('Team: Northern desk')).toBeVisible();
    expect(pageRequests(lists).at(-1)?.searchParams.get('scope')).toBe('all');
    // The bell keeps polling Mine and my teams while the page browses All users.
    const bell = lists.filter((url) => url.searchParams.has('hours'));
    expect(bell.length).toBeGreaterThan(0);
    expect(bell.every((url) => !url.searchParams.has('scope'))).toBe(true);
  });

  it('keeps the administrative view in the address', async () => {
    const { lists } = stubAlerts();
    renderApp('/warning?scope=all', 'admin');
    await screen.findByText('Uma private alert');
    expect(pageRequests(lists).every((url) => url.searchParams.get('scope') === 'all')).toBe(true);
  });

  it('never offers or requests All users for other roles', async () => {
    const { lists } = stubAlerts();
    renderApp('/warning?scope=all', 'user');
    await screen.findByRole('list', { name: 'Alerts' });
    expect(screen.queryByRole('group', { name: 'Whose alerts to show' })).not.toBeInTheDocument();
    expect(lists.every((url) => !url.searchParams.has('scope'))).toBe(true);
  });

  it('names the owner before a shared acknowledgement; cancel sends nothing', async () => {
    const { acks } = stubAlerts();
    const { user } = renderApp('/warning?scope=all', 'admin');
    const row = (await screen.findByText('Uma private alert')).closest('li')!;
    await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Uma User');
    expect(dialog).toHaveTextContent(/also clears it for Uma User/);
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(acks).toEqual([]);
    expect(within(row).getByRole('button', { name: 'Acknowledge' })).toBeEnabled();

    await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', {
        name: 'Acknowledge for everyone',
      }),
    );
    await waitFor(() => expect(within(row).getByText('acknowledged')).toBeInTheDocument());
    expect(acks).toEqual([theirs.id]);
  });

  it('leaves the alert unacknowledged when a shared acknowledgement fails', async () => {
    const { acks } = stubAlerts(() =>
      HttpResponse.json(
        { error: { code: 'server_error', message: 'Acknowledgement failed.' } },
        { status: 500 },
      ),
    );
    const { user } = renderApp('/warning?scope=all', 'admin');
    const row = (await screen.findByText('Uma private alert')).closest('li')!;
    await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Acknowledge for everyone' }));
    expect(await within(dialog).findByText('Acknowledgement failed.')).toBeVisible();
    expect(acks).toEqual([theirs.id]);
    expect(within(row).queryByText('acknowledged')).not.toBeInTheDocument();
  });

  it('acknowledges the administrator’s own alert without a warning', async () => {
    const { acks } = stubAlerts();
    const { user } = renderApp('/warning', 'admin');
    const row = (await screen.findByText('My own alert')).closest('li')!;
    await user.click(within(row).getByRole('button', { name: 'Acknowledge' }));
    await waitFor(() => expect(within(row).getByText('acknowledged')).toBeInTheDocument());
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(acks).toEqual([own.id]);
  });
});
