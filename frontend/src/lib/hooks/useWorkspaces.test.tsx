import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { TeamDetail } from '@/lib/api/teams';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { roster, team } from '@/test/fixtures.teams';

import { useWorkspaces } from './useWorkspaces';

const loaded = vi.hoisted(() => ({ details: [] as TeamDetail[] }));

vi.mock('@/lib/workspaceAuthority', () => ({
  loadWorkspaces: () => Promise.resolve(loaded.details),
  subscribeWorkspaceRefresh: () => () => undefined,
}));

const other = '99999999-9999-4999-8999-999999999999';

function plainUserAs(role: 'manager' | 'member', active = true): TeamDetail {
  return {
    ...roster,
    team: { ...team, is_active: active },
    members: roster.members.map((item) =>
      item.user_id === plainUser.id ? { ...item, role } : item,
    ),
  };
}

async function workspacesFor(user: typeof plainUser, details: TeamDetail[]) {
  loaded.details = details;
  useAuthStore.getState().setSession(tokenFor(user));
  const { result } = renderHook(() => useWorkspaces());
  await waitFor(() => expect(result.current.loading).toBe(false));
  return result.current;
}

describe('Workspace write authority mirrors the server rule', () => {
  it('lets a team manager without the global manager role manage team records', async () => {
    const workspaces = await workspacesFor(plainUser, [plainUserAs('manager')]);
    expect(workspaces.canManage({ team_id: team.id, created_by: other })).toBe(true);
  });

  it('limits ordinary members to their own records in an active team', async () => {
    const workspaces = await workspacesFor(plainUser, [plainUserAs('member')]);
    expect(workspaces.canManage({ team_id: team.id, created_by: plainUser.id })).toBe(true);
    expect(workspaces.canManage({ team_id: team.id, created_by: other })).toBe(false);
  });

  it('treats archived teams as read-only for everyone except administrators', async () => {
    const archived = [plainUserAs('manager', false)];
    const member = await workspacesFor(plainUser, archived);
    expect(member.canManage({ team_id: team.id, created_by: plainUser.id })).toBe(false);
    expect(member.canManage({ team_id: team.id, created_by: other })).toBe(false);
    const admin = await workspacesFor(adminUser, archived);
    expect(admin.canManage({ team_id: team.id, created_by: other })).toBe(true);
  });

  it('keeps personal records with their creator and denies unknown teams', async () => {
    const workspaces = await workspacesFor(plainUser, []);
    expect(workspaces.canManage({ team_id: null, created_by: plainUser.id })).toBe(true);
    expect(workspaces.canManage({ created_by: other })).toBe(false);
    expect(workspaces.canManage({ team_id: team.id, created_by: plainUser.id })).toBe(false);
  });

  it('denies every write when signed out', () => {
    loaded.details = [];
    useAuthStore.getState().clearSession();
    const { result } = renderHook(() => useWorkspaces());
    expect(result.current.canManage({ team_id: null, created_by: plainUser.id })).toBe(false);
  });
});
