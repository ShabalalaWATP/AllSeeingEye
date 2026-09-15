import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { adminUser, plainUser } from '@/test/fixtures';
import { manager, roster, setupTeams, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';

const archived = {
  ...team,
  id: '55555555-5555-4555-8555-555555555555',
  name: 'Old desk',
  is_active: false,
};

describe('TeamsPage states', () => {
  it('warns that list access changed and recovers on retry', async () => {
    let denied = true;
    const { user } = setupTeams(plainUser, roster, [
      http.get('/api/teams', () =>
        denied
          ? apiError(403, 'forbidden', 'Forbidden.')
          : HttpResponse.json({ items: [roster.team] }),
      ),
    ]);
    expect(await screen.findByText('Team access changed')).toBeInTheDocument();
    expect(screen.getByText(/Your team access may have changed/)).toBeInTheDocument();
    expect(screen.queryByText('Forbidden.')).not.toBeInTheDocument();
    denied = false;
    await user.click(screen.getByRole('button', { name: 'Retry teams' }));
    expect(await screen.findByLabelText('Team workspace')).toBeInTheDocument();
    expect(screen.queryByText('Team access changed')).not.toBeInTheDocument();
  });

  it('reports a failed team creation and keeps the form open', async () => {
    const { user } = setupTeams(plainUser, roster, [
      http.post('/api/teams', () =>
        apiError(429, 'rate_limited', 'Too many teams.', undefined, { 'Retry-After': '60' }),
      ),
    ]);
    await screen.findByLabelText('Team workspace');
    await user.click(screen.getByRole('button', { name: 'Create a team' }));
    expect(screen.getByRole('button', { name: 'Close create form' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    await user.type(screen.getByLabelText('New team name'), 'Desk two');
    await user.click(screen.getByRole('button', { name: 'Create team' }));
    expect(await screen.findByText('Too many attempts. Try again in 60 seconds.')).toBeVisible();
    expect(screen.getByLabelText('New team name')).toHaveValue('Desk two');

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByLabelText('New team name')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Create a team' }));
    await user.click(screen.getByRole('button', { name: 'Close create form' }));
    expect(screen.queryByLabelText('New team name')).not.toBeInTheDocument();
  });

  it('marks archived teams in the selector and opens the chosen workspace', async () => {
    const { user } = setupTeams(adminUser, roster, [
      http.get('/api/teams', () => HttpResponse.json({ items: [team, archived] })),
    ]);
    const selector = await screen.findByLabelText('Team workspace');
    expect(screen.getByRole('option', { name: 'Old desk (archived)' })).toBeInTheDocument();
    await user.selectOptions(selector, archived.id);
    expect(selector).toHaveValue(archived.id);
  });

  it('cancels creation from the empty state', async () => {
    const { user } = setupTeams(plainUser, roster, [
      http.get('/api/teams', () => HttpResponse.json({ items: [] })),
    ]);
    await screen.findByText('No workspaces yet');
    await user.click(screen.getByRole('button', { name: 'Create a team' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByLabelText('New team name')).not.toBeInTheDocument();
  });

  it('saves and clears a team description through settings', async () => {
    const { user, writes } = setupTeams(manager, {
      ...roster,
      team: { ...team, description: 'Watch the northern approaches' },
    });
    await user.click(await screen.findByText('Team settings'));
    const description = screen.getByLabelText(/Team description/);
    expect(description).toHaveValue('Watch the northern approaches');
    await user.clear(description);
    await user.click(screen.getByRole('button', { name: 'Save name' }));
    await screen.findByText('Team details saved.');

    await user.click(screen.getByText('Team settings'));
    await user.type(screen.getByLabelText(/Team description/), ' Maritime focus ');
    await user.click(screen.getByRole('button', { name: 'Save name' }));
    await waitFor(() => {
      expect(writes.map((write) => write.body)).toEqual([
        { name: team.name, description: null },
        { name: team.name, description: 'Maritime focus' },
      ]);
    });
  });
});
