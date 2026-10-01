import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { adminUser, plainUser } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { SELF_MODIFICATION_MESSAGE } from './UserRow';

installDialogStub();

async function findRow(name: string): Promise<HTMLElement> {
  const table = await screen.findByRole('table');
  const row = (await within(table).findByText(name)).closest('tr');
  if (row === null) throw new Error(`No row for ${name}`);
  return row;
}

function trackPatches(respond: (body: unknown) => Response | Promise<Response>) {
  const bodies: unknown[] = [];
  server.use(
    http.patch('/api/admin/users/:id', async ({ request }) => {
      const body = await request.json();
      bodies.push(body);
      return respond(body);
    }),
  );
  return bodies;
}

describe('administrator role changes', () => {
  it('shows the current and proposed role, and Cancel keeps the original', async () => {
    const bodies = trackPatches(() => HttpResponse.json(plainUser));
    const { user } = renderApp('/admin/users', 'admin');
    const select = within(await findRow('Uma User')).getByLabelText(`Role for ${plainUser.email}`);
    await user.selectOptions(select, 'admin');
    const dialog = await screen.findByRole('alertdialog', { name: 'Change role for Uma User?' });
    expect(dialog).toHaveTextContent(plainUser.email);
    expect(dialog).toHaveTextContent('Current role: User');
    expect(dialog).toHaveTextContent('Proposed role: Admin');
    expect(dialog).toHaveTextContent('must sign in again');
    expect(select).toHaveValue('user');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(select).toHaveValue('user');
    await waitFor(() => {
      expect(select).toHaveFocus();
    });
    expect(bodies).toEqual([]);
  });

  it('sends one change after confirmation and shows the new role', async () => {
    const bodies = trackPatches(async () => {
      await delay(150);
      return HttpResponse.json({ ...plainUser, role: 'admin' });
    });
    const { user } = renderApp('/admin/users', 'admin');
    const select = within(await findRow('Uma User')).getByLabelText(`Role for ${plainUser.email}`);
    await user.selectOptions(select, 'admin');
    const dialog = await screen.findByRole('alertdialog');
    const confirm = within(dialog).getByRole('button', { name: 'Change role' });
    await user.click(confirm);
    await user.click(confirm);
    await waitFor(() => {
      expect(select).toHaveValue('admin');
    });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(bodies).toEqual([{ role: 'admin' }]);
  });

  it('keeps the current role and a permission refusal visible with a retry', async () => {
    const bodies = trackPatches(() =>
      apiError(403, 'forbidden', 'Only an administrator can do this.'),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const select = within(await findRow('Uma User')).getByLabelText(`Role for ${plainUser.email}`);
    await user.selectOptions(select, 'admin');
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Change role' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Only an administrator can do this.',
    );
    expect(select).toHaveValue('user');
    await user.click(within(dialog).getByRole('button', { name: 'Change role' }));
    await waitFor(() => {
      expect(bodies).toHaveLength(2);
    });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(select).toHaveValue('user');
  });

  it('explains the self-modification refusal inside the confirmation', async () => {
    const { user } = renderApp('/admin/users', 'admin');
    const select = within(await findRow('Ada Admin')).getByLabelText(`Role for ${adminUser.email}`);
    await user.selectOptions(select, 'user');
    const dialog = await screen.findByRole('alertdialog', { name: 'Change role for Ada Admin?' });
    await user.click(within(dialog).getByRole('button', { name: 'Change role' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(SELF_MODIFICATION_MESSAGE);
    expect(select).toHaveValue('admin');
  });
});

describe('administrator access changes', () => {
  it('confirms pausing access, naming the account and what ends', async () => {
    const bodies = trackPatches(() => HttpResponse.json({ ...plainUser, is_active: false }));
    const { user } = renderApp('/admin/users', 'admin');
    const row = await findRow('Uma User');
    const checkbox = within(row).getByRole('checkbox', { name: 'Active' });
    await user.click(checkbox);
    const dialog = await screen.findByRole('alertdialog', {
      name: 'Pause access for Uma User?',
    });
    expect(checkbox).toBeChecked();
    expect(dialog).toHaveTextContent('Current access: Active');
    expect(dialog).toHaveTextContent('Proposed access: Paused');
    expect(dialog).toHaveTextContent('cannot sign in');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(checkbox).toBeChecked();
    expect(bodies).toEqual([]);
    await user.click(checkbox);
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', {
        name: 'Pause access',
      }),
    );
    await waitFor(() => {
      expect(checkbox).not.toBeChecked();
    });
    expect(bodies).toEqual([{ is_active: false }]);
  });

  it('states the access change when restoring a paused account', async () => {
    server.use(
      http.get('/api/admin/users', () =>
        HttpResponse.json({ items: [adminUser, { ...plainUser, is_active: false }] }),
      ),
    );
    const bodies = trackPatches(() => HttpResponse.json({ ...plainUser, is_active: true }));
    const { user } = renderApp('/admin/users', 'admin');
    const checkbox = within(await findRow('Uma User')).getByRole('checkbox', { name: 'Active' });
    await user.click(checkbox);
    const dialog = await screen.findByRole('alertdialog', {
      name: 'Restore access for Uma User?',
    });
    expect(dialog).toHaveTextContent('Current access: Paused');
    expect(dialog).toHaveTextContent('Proposed access: Active');
    expect(dialog).toHaveTextContent('can sign in again');
    expect(checkbox).not.toBeChecked();
    await user.click(within(dialog).getByRole('button', { name: 'Restore access' }));
    await waitFor(() => {
      expect(checkbox).toBeChecked();
    });
    expect(bodies).toEqual([{ is_active: true }]);
  });
});
