import { render } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { RequestHandler } from 'msw';
import { createElement } from 'react';

import type { User } from '@/lib/api/schemas';
import type { Team, TeamDetail, TeamMember } from '@/lib/api/teams';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';

import TeamsPage from '@/features/teams/TeamsPage';

export const manager: User = {
  ...plainUser,
  id: '33333333-3333-4333-8333-333333333333',
  role: 'manager',
  email: 'manager@example.com',
  display_name: 'Mina Manager',
};
export const team: Team = {
  id: '44444444-4444-4444-8444-444444444444',
  name: 'Northern desk',
  is_active: true,
  created_by: adminUser.id,
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  description: null,
};
function member(user: User, role: TeamMember['role']): TeamMember {
  return {
    user_id: user.id,
    display_name: user.display_name,
    username: user.id === manager.id ? 'mina_manager' : null,
    account_role: user.role,
    is_active: user.is_active,
    role,
    joined_at: team.created_at,
  };
}
export const roster: TeamDetail = {
  team,
  members: [member(manager, 'manager'), member(plainUser, 'member')],
};

export function setupTeams(
  actor: User = plainUser,
  initial: TeamDetail = roster,
  handlers: RequestHandler[] = [],
) {
  let detail = structuredClone(initial);
  const writes: { method: string; body?: unknown; userId?: string }[] = [];
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [detail.team] })),
    http.get('/api/teams/:id', () => HttpResponse.json(detail)),
    http.post('/api/teams', async ({ request }) => {
      const body = (await request.json()) as { name: string };
      writes.push({ method: 'POST', body });
      detail = {
        team: { ...team, id: '55555555-5555-4555-8555-555555555555', name: body.name },
        members: [],
      };
      return HttpResponse.json(detail.team, { status: 201 });
    }),
    http.patch('/api/teams/:id', async ({ request }) => {
      const body = (await request.json()) as Partial<Team>;
      writes.push({ method: 'PATCH', body });
      detail = { ...detail, team: { ...detail.team, ...body } };
      return HttpResponse.json(detail.team);
    }),
    http.put('/api/teams/:id/members', async ({ request }) => {
      const body = (await request.json()) as { email: string; role: TeamMember['role'] };
      writes.push({ method: 'PUT', body });
      return HttpResponse.json({
        team_id: team.id,
        user_id: plainUser.id,
        role: body.role,
        joined_at: team.created_at,
      });
    }),
    http.patch('/api/teams/:id/members/:userId', async ({ params, request }) => {
      const userId = String(params.userId);
      const body = (await request.json()) as { role: TeamMember['role'] };
      writes.push({ method: 'PATCH', userId, body });
      detail.members = detail.members.map((item) =>
        item.user_id === userId ? { ...item, role: body.role } : item,
      );
      return HttpResponse.json({
        team_id: team.id,
        user_id: userId,
        role: body.role,
        joined_at: team.created_at,
      });
    }),
    http.post('/api/teams/:id/leave', () => {
      writes.push({ method: 'LEAVE' });
      detail.members = detail.members.filter((item) => item.user_id !== actor.id);
      return new HttpResponse(null, { status: 204 });
    }),
    http.delete('/api/teams/:id/members/:userId', ({ params }) => {
      const userId = String(params.userId);
      writes.push({ method: 'DELETE', userId });
      detail.members = detail.members.filter((item) => item.user_id !== userId);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  server.use(...handlers);
  useAuthStore.getState().setSession(tokenFor(actor));
  const user = userEvent.setup();
  return { user, writes, ...render(createElement(TeamsPage)) };
}
