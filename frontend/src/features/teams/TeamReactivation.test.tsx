import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { adminUser, plainUser } from '@/test/fixtures';
import { manager, roster, setupTeams, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

const archived = {
  ...roster,
  team: { ...team, is_active: false },
  members: roster.members.map((member) =>
    member.role === 'manager' ? { ...member, is_active: false } : member,
  ),
};

it('requires an explicit active Manager when reactivating an orphaned team', async () => {
  const { user, writes } = setupTeams(adminUser, archived, [
    http.get('/api/admin/users', () =>
      HttpResponse.json({ items: [adminUser, plainUser, { ...manager, is_active: false }] }),
    ),
  ]);
  await user.click(await screen.findByText('Team settings'));
  const select = await screen.findByRole('combobox', { name: 'Manager on reactivation' });
  const submit = screen.getByRole('button', { name: 'Reactivate team' });
  expect(submit).toBeDisabled();
  expect(screen.queryByRole('option', { name: /Mina Manager|Ada Admin/ })).not.toBeInTheDocument();
  await user.selectOptions(select, plainUser.id);
  await user.click(submit);
  await waitFor(() => {
    expect(writes).toEqual([
      { method: 'PATCH', body: { is_active: true, reactivation_manager_id: plainUser.id } },
    ]);
  });
  expect(await screen.findByText('Team reactivated.')).toBeInTheDocument();
});

it('keeps reactivation blocked when eligible accounts cannot be loaded, with retry', async () => {
  const { user, writes } = setupTeams(adminUser, archived, [
    http.get('/api/admin/users', () => apiError(503, 'unavailable', 'Accounts unavailable.')),
  ]);
  await user.click(await screen.findByText('Team settings'));
  expect(await screen.findByText('Accounts unavailable.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Reactivate team' })).not.toBeInTheDocument();
  server.use(http.get('/api/admin/users', () => HttpResponse.json({ items: [adminUser] })));
  await user.click(screen.getByRole('button', { name: 'Retry accounts' }));
  expect(await screen.findByText(/Activate another account in Users/)).toBeInTheDocument();
  expect(writes).toEqual([]);
});
