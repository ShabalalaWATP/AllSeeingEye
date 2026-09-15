import { render } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { TeamBoard } from '@/features/teams/TeamBoard';
import type { TeamCapabilities } from '@/features/teams/teamCapabilities';
import type { TeamBoardPage, TeamBoardPost } from '@/lib/api/teamBoard';

import { plainUser } from './fixtures';
import { team } from './fixtures.teams';
import { apiError } from './handlers';
import { server } from './server';

export const boardBase = `/api/teams/${team.id}/board`;

export function boardPost(overrides: Partial<TeamBoardPost>): TeamBoardPost {
  return {
    id: '66666666-6666-4666-8666-666666666661',
    team_id: team.id,
    author_id: plainUser.id,
    author_name: plainUser.display_name,
    text: 'Handover note',
    created_at: '2026-09-15T08:00:00Z',
    updated_at: '2026-09-15T08:00:00Z',
    edited_at: null,
    parent_id: null,
    is_pinned: false,
    deleted_at: null,
    removal: null,
    revision: 1,
    ...overrides,
  };
}

export function boardPage(
  items: TeamBoardPost[],
  options: { replies?: TeamBoardPost[]; unread?: number; nextOffset?: number | null } = {},
): TeamBoardPage {
  return {
    items,
    replies: options.replies ?? [],
    total: items.length,
    offset: 0,
    limit: 20,
    next_offset: options.nextOffset ?? null,
    unread_count: options.unread ?? 0,
  };
}

export const memberBoardCapabilities: TeamCapabilities = {
  isAdmin: false,
  isMember: true,
  isManager: false,
  teamIsActive: true,
  canCreateTeam: true,
  canManageMembers: false,
  canManageTeam: false,
  canLeave: true,
};

export const managerBoardCapabilities: TeamCapabilities = {
  ...memberBoardCapabilities,
  isManager: true,
  canManageMembers: true,
  canManageTeam: true,
};

/** Serve the first board page from a snapshot callback and record requests and receipts. */
export function serveBoard(firstPage: () => TeamBoardPage | 404 | 503, olderPage?: TeamBoardPage) {
  const requests: string[] = [];
  const reads: unknown[] = [];
  server.use(
    http.get(`${boardBase}/posts`, ({ request }) => {
      const offset = new URL(request.url).searchParams.get('offset') ?? '0';
      requests.push(offset);
      if (offset !== '0' && olderPage) return HttpResponse.json(olderPage);
      const page = firstPage();
      if (page === 404) return apiError(404, 'not_found', 'Not found.');
      if (page === 503) return apiError(503, 'unavailable', 'Unavailable.');
      return HttpResponse.json(page);
    }),
    http.post(`${boardBase}/read`, async ({ request }) => {
      reads.push(await request.json());
      return HttpResponse.json({ unread_count: 0 });
    }),
  );
  return { requests, reads };
}

export function renderTeamBoard(userId: string, capabilities: TeamCapabilities) {
  const user = userEvent.setup();
  render(
    <TeamBoard teamId={team.id} teamName={team.name} userId={userId} capabilities={capabilities} />,
  );
  return user;
}
