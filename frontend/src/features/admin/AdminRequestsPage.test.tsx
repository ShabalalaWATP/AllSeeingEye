import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ACTIVATION_LINK, pendingRequests, plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function findRow(name: string): Promise<HTMLElement> {
  const cell = await screen.findByText(name);
  const row = cell.closest('tr');
  if (row === null) throw new Error(`No row for ${name}`);
  return row;
}

describe('AdminRequestsPage', () => {
  it('approves with a role and shows the activation link with copy and expiry', async () => {
    let body: unknown = null;
    server.use(
      http.post('/api/admin/account-requests/:id/approve', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          user: { ...plainUser, role: 'admin' },
          activation_link: ACTIVATION_LINK,
          expires_at: '2026-09-11T12:00:00Z',
        });
      }),
    );
    const { user } = renderApp('/admin/requests', 'admin');
    const row = await findRow('Nia Newcomer');
    expect(within(row).getByText('Analyst on the regional desk.')).toBeInTheDocument();

    await user.selectOptions(within(row).getByLabelText('Role'), 'admin');
    await user.click(within(row).getByRole('button', { name: 'Approve' }));

    expect(await screen.findByText('Activation link for newcomer@example.com')).toBeInTheDocument();
    expect(body).toEqual({ role: 'admin' });
    expect(screen.getByLabelText('Activation link for newcomer@example.com')).toHaveValue(
      ACTIVATION_LINK,
    );
    expect(screen.getByText(/^Expires 11 Sep\w* 2026, 12:00 UTC$/)).toBeInTheDocument();
    expect(screen.queryByText('Nia Newcomer')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument();
    // user-event installs its own clipboard stub, so read back through it.
    expect(await navigator.clipboard.readText()).toBe(ACTIVATION_LINK);
  });

  it('shows a plain confirmation when the server emailed the link itself', async () => {
    server.use(
      http.post('/api/admin/account-requests/:id/approve', () =>
        HttpResponse.json({ user: plainUser, activation_link: null, expires_at: '2026-09-11T12:00:00Z' }),
      ),
    );
    const { user } = renderApp('/admin/requests', 'admin');
    const row = await findRow('Sam Second');
    expect(within(row).getByText('No reason given')).toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Approve' }));
    expect(await screen.findByText(/second@example.com approved/)).toBeInTheDocument();
  });

  it('rejects with an optional reason', async () => {
    let body: unknown = null;
    server.use(
      http.post('/api/admin/account-requests/:id/reject', async ({ request }) => {
        body = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/admin/requests', 'admin');
    const row = await findRow('Nia Newcomer');
    await user.click(within(row).getByRole('button', { name: 'Reject' }));
    await user.type(within(row).getByLabelText('Reason (optional)'), 'Duplicate request');
    await user.click(within(row).getByRole('button', { name: 'Confirm rejection' }));

    expect(
      await screen.findByText('The request from newcomer@example.com was rejected.'),
    ).toBeInTheDocument();
    expect(body).toEqual({ reason: 'Duplicate request' });
    expect(screen.queryByText('Nia Newcomer')).not.toBeInTheDocument();
    expect(screen.getByText('Sam Second')).toBeInTheDocument();
  });

  it('shows decision failures inline', async () => {
    server.use(
      http.post('/api/admin/account-requests/:id/approve', () =>
        apiError(409, 'already_decided', 'This request has already been decided.'),
      ),
    );
    const { user } = renderApp('/admin/requests', 'admin');
    const row = await findRow('Nia Newcomer');
    await user.click(within(row).getByRole('button', { name: 'Approve' }));
    expect(await within(row).findByRole('alert')).toHaveTextContent(
      'This request has already been decided.',
    );
  });

  it('shows the empty state and load errors', async () => {
    server.use(http.get('/api/admin/account-requests', () => HttpResponse.json({ items: [] })));
    const first = renderApp('/admin/requests', 'admin');
    expect(await screen.findByText('No pending requests.')).toBeInTheDocument();
    first.unmount();

    server.use(
      http.get('/api/admin/account-requests', () => apiError(500, 'server_error', 'Database down.')),
    );
    renderApp('/admin/requests', 'admin');
    expect(await screen.findByRole('alert')).toHaveTextContent('Database down.');
    expect(pendingRequests).toHaveLength(2);
  });
});
