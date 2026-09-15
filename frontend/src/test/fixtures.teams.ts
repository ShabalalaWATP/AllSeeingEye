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
    email: user.email,
    display_name: user.display_name,
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
      detail.members = detail.members.map((item) =>
        item.email === body.email ? { ...item, role: body.role } : item,
      );
      return HttpResponse.json({
        team_id: team.id,
        user_id: plainUser.id,
        role: body.role,
        joined_at: team.created_at,
      });
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
