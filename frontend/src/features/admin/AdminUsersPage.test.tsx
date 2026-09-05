import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { RESET_LINK, adminUser, plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { SELF_MODIFICATION_MESSAGE } from './UserRow';

async function findRow(name: string): Promise<HTMLElement> {
  // Scope to the table: the signed-in admin's name also appears in the top bar.
  const table = await screen.findByRole('table');
  const cell = await within(table).findByText(name);
  const row = cell.closest('tr');
  if (row === null) throw new Error(`No row for ${name}`);
  return row;
}

describe('AdminUsersPage', () => {
  it('changes a role through the select', async () => {
    let body: unknown = null;
    server.use(
      http.patch('/api/admin/users/:id', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...plainUser, role: 'admin' });
      }),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Uma User');
    expect(within(row).getByText('Never')).toBeInTheDocument();
    const select = within(row).getByLabelText(`Role for ${plainUser.email}`);
    await user.selectOptions(select, 'admin');
    await waitFor(() => {
      expect(select).toHaveValue('admin');
    });
    expect(body).toEqual({ role: 'admin' });
  });

  it('toggles the active flag', async () => {
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Uma User');
    const checkbox = within(row).getByRole('checkbox', { name: 'Active' });
    expect(checkbox).toBeChecked();
    await user.click(checkbox);
    await waitFor(() => {
      expect(checkbox).not.toBeChecked();
    });
  });

  it('shows the guard message when an admin edits their own account', async () => {
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Ada Admin');
    const select = within(row).getByLabelText(`Role for ${adminUser.email}`);
    await user.selectOptions(select, 'user');
    expect(await within(row).findByRole('alert')).toHaveTextContent(SELF_MODIFICATION_MESSAGE);
    expect(select).toHaveValue('admin');
  });

  it('issues a reset link and shows it with its expiry', async () => {
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Uma User');
    await user.click(within(row).getByRole('button', { name: 'Issue reset link' }));
    expect(await screen.findByText(`Reset link for ${plainUser.email}`)).toBeInTheDocument();
    expect(screen.getByLabelText(`Reset link for ${plainUser.email}`)).toHaveValue(RESET_LINK);
    expect(screen.getByText(/^Expires 4 Sep\w* 2026, 10:30 UTC$/)).toBeInTheDocument();
  });

  it('shows other failures with the API message', async () => {
    server.use(
      http.post('/api/admin/users/:id/reset-link', () =>
        apiError(404, 'not_found', 'User not found.'),
      ),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Uma User');
    await user.click(within(row).getByRole('button', { name: 'Issue reset link' }));
    expect(await within(row).findByRole('alert')).toHaveTextContent('User not found.');
  });

  it('shows load errors', async () => {
    server.use(http.get('/api/admin/users', () => apiError(500, 'server_error', 'Database down.')));
    renderApp('/admin/users', 'admin');
    expect(await screen.findByRole('alert')).toHaveTextContent('Database down.');
  });
});
