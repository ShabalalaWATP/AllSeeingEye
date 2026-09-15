import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TeamDashboard } from '@/lib/api/teamBoard';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

import type { TeamCapabilities } from './teamCapabilities';
import { TeamOverview } from './TeamOverview';

const member: TeamCapabilities = {
  isAdmin: false,
  isMember: true,
  isManager: false,
  teamIsActive: true,
  canCreateTeam: true,
  canManageMembers: false,
  canManageTeam: false,
  canLeave: true,
};

function dashboard(role: TeamDashboard['team']['role']): TeamDashboard {
  return {
    team: {
      id: team.id,
      name: team.name,
      description: null,
      is_active: true,
      role,
      member_count: 2,
    },
    pinned: [],
    unread_count: 7,
    recent_reports: [],
    upcoming_runs: [],
    action_items: [
      {
        kind: 'edition_blocked',
        schedule_id: '99999999-9999-4999-8999-999999999991',
        schedule_name: 'Blocked brief',
        occurred_at: '2026-09-14T06:00:00Z',
        edition_id: null,
      },
    ],
  };
}

async function renderFor(role: TeamDashboard['team']['role'], capabilities: TeamCapabilities) {
  server.use(http.get(`/api/teams/${team.id}/dashboard`, () => HttpResponse.json(dashboard(role))));
  const onTabChange = vi.fn();
  const user = userEvent.setup();
  render(<TeamOverview teamId={team.id} capabilities={capabilities} onTabChange={onTabChange} />);
  const stats = await screen.findByText('Your role');
  return { user, onTabChange, stats: stats.parentElement! };
}

describe('TeamOverview roles and actions', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('labels managers and sends them to manage access', async () => {
    const { user, onTabChange, stats } = await renderFor('manager', {
      ...member,
      isManager: true,
      canManageMembers: true,
    });
    expect(within(stats).getByText('Manager')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    const actions = within(screen.getByRole('region', { name: 'Action needed' }));
    expect(actions.getByText(/A run was blocked on/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Manage access' }));
    expect(onTabChange).toHaveBeenCalledWith('members');
  });

  it('labels an administrator without team membership', async () => {
    const { stats } = await renderFor(null, { ...member, isAdmin: true, isMember: false });
    expect(within(stats).getByText('Administrator')).toBeInTheDocument();
  });

  it('labels an account without membership and offers the member list', async () => {
    const { user, onTabChange, stats } = await renderFor(null, { ...member, isMember: false });
    expect(within(stats).getByText('No membership')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open members' }));
    expect(onTabChange).toHaveBeenCalledWith('members');
  });
});
