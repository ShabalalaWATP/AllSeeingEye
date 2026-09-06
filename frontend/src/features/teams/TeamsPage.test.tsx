import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { manager, roster, setupTeams, team } from '@/test/fixtures.teams';

async function memberRow(name: string) {
  const table = await screen.findByRole('table', { name: 'Team members' });
  const row = within(table).getByText(name).closest('tr');
  if (!row) throw new Error('Missing member row');
  return within(row);
}

describe('TeamsPage', () => {
  it('lets users read their rosters without membership or account controls', async () => {
    setupTeams();
    await memberRow('Uma User');
    expect(screen.getByText(/You can view this roster/)).toBeInTheDocument();
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Remove|Make|reset/i })).not.toBeInTheDocument();
  });

  it('requires both a manager account and manager membership', async () => {
    setupTeams(manager, {
      ...roster,
      members: roster.members.map((member) => ({ ...member, role: 'member' })),
    });
    await memberRow('Mina Manager');
    expect(screen.queryByRole('form', { name: 'Add team member' })).not.toBeInTheDocument();
  });

  it('does not grant manager authority to a user with a stale manager designation', async () => {
    setupTeams(plainUser, {
      ...roster,
      members: roster.members.map((member) => ({ ...member, role: 'manager' })),
    });
    await memberRow('Uma User');
    expect(screen.queryByRole('button', { name: 'Remove member' })).not.toBeInTheDocument();
  });

  it('lets designated managers add ordinary members by email without an account directory', async () => {
    const { user, writes } = setupTeams(manager);
    await user.type(await screen.findByLabelText('Account email'), 'new@example.com');
    expect(screen.queryByLabelText('Team role')).not.toBeInTheDocument();
    expect(screen.queryByText('Team settings')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add member' }));
    expect(await screen.findByText('Membership saved.')).toBeInTheDocument();
    expect(writes).toEqual([{ method: 'PUT', body: { email: 'new@example.com', role: 'member' } }]);
    expect((await memberRow('Mina Manager')).queryByRole('button')).not.toBeInTheDocument();
  });

  it('confirms removal and supports cancellation without sending a request', async () => {
    const { user, writes } = setupTeams(manager);
    const row = await memberRow('Uma User');
    await user.click(row.getByRole('button', { name: 'Remove member' }));
    await user.click(row.getByRole('button', { name: 'Cancel' }));
    expect(writes).toEqual([]);
    await user.click(row.getByRole('button', { name: 'Remove member' }));
    await user.click(row.getByRole('button', { name: 'Confirm remove member' }));
    await waitFor(() => {
      expect(screen.queryByText('Uma User')).not.toBeInTheDocument();
    });
    expect(writes).toEqual([{ method: 'DELETE', userId: plainUser.id }]);
  });

  it('gives administrators explicit membership role controls', async () => {
    const { user, writes } = setupTeams(adminUser);
    await user.type(await screen.findByLabelText('Account email'), 'lead@example.com');
    await user.selectOptions(screen.getByLabelText('Team role'), 'manager');
    await user.click(screen.getByRole('button', { name: 'Add member' }));
    await screen.findByText('Membership saved.');
    expect(writes[0]).toEqual({
      method: 'PUT',
      body: { email: 'lead@example.com', role: 'manager' },
    });
    await user.click(
      (await memberRow('Mina Manager')).getByRole('button', { name: 'Make member' }),
    );
    await screen.findByText('Team role updated.');
    await user.click(
      (await memberRow('Mina Manager')).getByRole('button', { name: 'Make manager' }),
    );
    await waitFor(() => {
      expect(writes).toHaveLength(3);
    });
    expect(writes[2]).toEqual({ method: 'PUT', body: { email: manager.email, role: 'manager' } });
  });

  it('creates and selects a named team', async () => {
    const { user, writes } = setupTeams(adminUser);
    await user.click(screen.getByText('Create a team'));
    await user.type(screen.getByLabelText('New team name'), 'Southern desk');
    await user.click(screen.getByRole('button', { name: 'Create team' }));
    expect(await screen.findByRole('heading', { name: 'Southern desk' })).toBeInTheDocument();
    expect(screen.getByText('No members in this team.')).toBeInTheDocument();
    expect(writes[0]).toEqual({ method: 'POST', body: { name: 'Southern desk' } });
  });

  it('renames, archives and reactivates teams through administrator settings', async () => {
    const { user, writes } = setupTeams(adminUser);
    await user.click(await screen.findByText('Team settings'));
    await user.clear(screen.getByLabelText('Team name'));
    await user.type(screen.getByLabelText('Team name'), 'Renamed desk');
    await user.click(screen.getByRole('button', { name: 'Save name' }));
    await screen.findByRole('heading', { name: 'Renamed desk' });
    await user.click(screen.getByText('Team settings'));
    await user.click(screen.getByRole('button', { name: 'Archive team' }));
    expect(writes).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Confirm archive team' }));
    await screen.findByText(/This team is archived/);
    expect(screen.queryByRole('form', { name: 'Add team member' })).not.toBeInTheDocument();
    await user.click(screen.getByText('Team settings'));
    await user.click(screen.getByRole('button', { name: 'Reactivate team' }));
    await screen.findByRole('form', { name: 'Add team member' });
    expect(writes.map((write) => write.body)).toEqual([
      { name: 'Renamed desk' },
      { is_active: false },
      { is_active: true },
    ]);
  });

  it('keeps archived teams read-only for managers', async () => {
    setupTeams(manager, { ...roster, team: { ...team, is_active: false } });
    await screen.findByText(/This team is archived/);
    expect(screen.queryByRole('button', { name: /Add|Remove|Reactivate/ })).not.toBeInTheDocument();
  });

  it('discards stale roster authority after a denied membership change', async () => {
    const { user } = setupTeams(manager);
    await screen.findByLabelText('Account email');
    server.use(
      http.put('/api/teams/:id/members', () => apiError(403, 'forbidden', 'Membership changed.')),
      http.get('/api/teams/:id', () => apiError(404, 'not_found', 'Team not found.')),
    );
    await user.type(screen.getByLabelText('Account email'), 'admin@example.com');
    await user.click(screen.getByRole('button', { name: 'Add member' }));
    expect(await screen.findByText('Membership changed.')).toBeInTheDocument();
    await screen.findByText('Team not found.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Add team member' })).not.toBeInTheDocument();
  });

  it('clears the old roster when the signed-in identity changes', async () => {
    setupTeams(adminUser);
    await memberRow('Mina Manager');
    server.use(http.get('/api/teams', () => HttpResponse.json({ items: [] })));
    act(() => {
      useAuthStore.getState().setSession(tokenFor(plainUser));
    });
    expect(screen.queryByText('Mina Manager')).not.toBeInTheDocument();
    await screen.findByText(/You are not assigned to a team/);
    act(() => {
      useAuthStore.getState().clearSession();
    });
    expect(screen.queryByRole('heading', { name: 'Teams' })).not.toBeInTheDocument();
  });

  it('shows useful empty and failed-list states with retry', async () => {
    const { user } = setupTeams(adminUser, roster, [
      http.get('/api/teams', () => apiError(500, 'server_error', 'Teams unavailable.')),
    ]);
    await screen.findByText('Teams unavailable.');
    server.use(http.get('/api/teams', () => HttpResponse.json({ items: [] })));
    await user.click(screen.getByRole('button', { name: 'Retry teams' }));
    await screen.findByText(/No teams yet/);
  });

  it('rejects malformed server rosters and retries successfully', async () => {
    const { user } = setupTeams(plainUser, roster, [
      http.get('/api/teams/:id', () =>
        HttpResponse.json({
          ...roster,
          members: [{ ...roster.members[0], account_role: 'superadmin' }],
        }),
      ),
    ]);
    await screen.findByText('The server sent an unexpected response.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    server.use(http.get('/api/teams/:id', () => HttpResponse.json(roster)));
    await user.click(screen.getByRole('button', { name: 'Retry roster' }));
    await memberRow('Mina Manager');
    await user.click(screen.getByRole('button', { name: 'Refresh roster' }));
    await memberRow('Uma User');
  });
});
