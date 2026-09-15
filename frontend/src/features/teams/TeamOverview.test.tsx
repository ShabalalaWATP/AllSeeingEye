import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TeamDashboard } from '@/lib/api/teamBoard';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { manager, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import type { TeamCapabilities } from './teamCapabilities';
import { TeamOverview } from './TeamOverview';

const capabilities: TeamCapabilities = {
  isAdmin: false,
  isMember: true,
  isManager: false,
  teamIsActive: true,
  canCreateTeam: true,
  canManageMembers: false,
  canManageTeam: false,
  canLeave: true,
};

const dashboard: TeamDashboard = {
  team: {
    id: team.id,
    name: team.name,
    description: null,
    is_active: true,
    role: 'member',
    member_count: 4,
  },
  pinned: [
    {
      id: '77777777-7777-4777-8777-777777777771',
      team_id: team.id,
      author_id: manager.id,
      author_name: manager.display_name,
      text: 'Standing orders for the week',
      created_at: '2026-09-15T08:00:00Z',
      updated_at: '2026-09-15T08:00:00Z',
      edited_at: null,
      parent_id: null,
      is_pinned: true,
      deleted_at: null,
      removal: null,
      revision: 2,
    },
  ],
  unread_count: 120,
  recent_reports: [
    {
      id: '88888888-8888-4888-8888-888888888881',
      title: 'Baltic shipping assessment',
      template: 'ask',
      status: 'final',
      latest_version: 3,
      created_at: '2026-09-14T12:00:00Z',
    },
  ],
  upcoming_runs: [
    {
      schedule_id: '99999999-9999-4999-8999-999999999991',
      name: 'Morning maritime brief',
      cadence: 'daily',
      next_run_at: '2026-09-16T06:00:00Z',
    },
  ],
  action_items: [
    {
      kind: 'owner_not_member',
      schedule_id: '99999999-9999-4999-8999-999999999992',
      schedule_name: 'Former analyst watch',
      occurred_at: '2026-09-16T07:00:00Z',
      edition_id: null,
    },
    {
      kind: 'edition_failed',
      schedule_id: '99999999-9999-4999-8999-999999999991',
      schedule_name: 'Morning maritime brief',
      occurred_at: '2026-09-14T06:00:00Z',
      edition_id: '99999999-9999-4999-8999-999999999993',
    },
  ],
};

function renderOverview(onTabChange = vi.fn()) {
  const user = userEvent.setup();
  render(<TeamOverview teamId={team.id} capabilities={capabilities} onTabChange={onTabChange} />);
  return { user, onTabChange };
}

describe('TeamOverview', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('renders pinned posts, exact report links, next runs and action-needed items', async () => {
    server.use(http.get(`/api/teams/${team.id}/dashboard`, () => HttpResponse.json(dashboard)));
    const { user, onTabChange } = renderOverview();

    expect(await screen.findByText('Standing orders for the week')).toBeInTheDocument();
    expect(screen.getByText('100+')).toBeInTheDocument();
    expect(screen.getByText('Member')).toBeInTheDocument();

    const reports = within(screen.getByRole('region', { name: 'Recent shared reports' }));
    expect(reports.getByRole('link', { name: 'Baltic shipping assessment' })).toHaveAttribute(
      'href',
      '/reports/88888888-8888-4888-8888-888888888881?version=3',
    );
    const runs = within(screen.getByRole('region', { name: 'Next subscription runs' }));
    expect(runs.getByRole('link', { name: 'Morning maritime brief' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
    const actions = within(screen.getByRole('region', { name: 'Action needed' }));
    expect(actions.getByText(/no longer an active member/)).toBeInTheDocument();
    expect(actions.getByText(/A run failed/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Open board' }));
    expect(onTabChange).toHaveBeenCalledWith('board');
  });

  it('shows empty states when the team has no shared work yet', async () => {
    server.use(
      http.get(`/api/teams/${team.id}/dashboard`, () =>
        HttpResponse.json({
          ...dashboard,
          pinned: [],
          unread_count: 0,
          recent_reports: [],
          upcoming_runs: [],
          action_items: [],
        }),
      ),
    );
    renderOverview();
    expect(
      await screen.findByText('No reports have been shared with this team yet.'),
    ).toBeInTheDocument();
    expect(screen.getByText('No team subscriptions are scheduled.')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Action needed' })).not.toBeInTheDocument();
  });

  it('reports revoked access and retries on request', async () => {
    let revoked = true;
    server.use(
      http.get(`/api/teams/${team.id}/dashboard`, () =>
        revoked ? apiError(404, 'not_found', 'Not found.') : HttpResponse.json(dashboard),
      ),
    );
    const { user } = renderOverview();
    expect(await screen.findByText('Team access changed')).toBeInTheDocument();
    revoked = false;
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Standing orders for the week')).toBeInTheDocument();
  });
});
