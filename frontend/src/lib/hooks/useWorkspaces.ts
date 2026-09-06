import { useCallback, useEffect, useState } from 'react';

import { loadWorkspaces, subscribeWorkspaceRefresh } from '@/lib/workspaceAuthority';
import { useAuthStore } from '@/stores/auth';

import { useScopedResource } from './useScopedResource';

export function useWorkspaces() {
  const user = useAuthStore((state) => state.user);
  const resource = useScopedResource(loadWorkspaces);
  const { refresh } = resource;
  useEffect(() => subscribeWorkspaceRefresh(() => void refresh()), [refresh]);
  const teams = (resource.data ?? []).filter(
    (detail) =>
      user?.role === 'admin' ||
      detail.members.some((member) => member.user_id === user?.id && member.is_active),
  );
  const label = (teamId: string | null | undefined) =>
    teamId
      ? `Team: ${teams.find((detail) => detail.team.id === teamId)?.team.name ?? 'unavailable'}`
      : 'Personal';
  const canManage = (record: { created_by: string; team_id?: string | null }) => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    const detail = teams.find((entry) => entry.team.id === record.team_id);
    if (record.team_id && !detail) return false;
    if (record.created_by === user.id) return true;
    return (
      user.role === 'manager' &&
      detail?.members.some(
        (member) =>
          member.user_id === user.id &&
          member.role === 'manager' &&
          member.account_role === 'manager',
      ) === true
    );
  };
  const canAcknowledge = (teamId: string | null | undefined) =>
    Boolean(user) &&
    (user?.role === 'admin' || !teamId || teams.some((entry) => entry.team.id === teamId));
  return { ...resource, teams, label, canManage, canAcknowledge };
}

export type Workspaces = ReturnType<typeof useWorkspaces>;

/** Selection is local and cannot survive an identity or access invalidation. */
export function useWorkspaceSelection(workspaces: Workspaces) {
  const [choice, setChoice] = useState({ key: workspaces.key, id: '' });
  const selected = choice.key === workspaces.key ? choice.id : '';
  const valid = !selected || workspaces.teams.some((entry) => entry.team.id === selected);
  const select = useCallback(
    (id: string) => setChoice({ key: workspaces.key, id }),
    [workspaces.key],
  );
  return {
    teamId: selected,
    select,
    valid,
    ready: selected === '' || (!workspaces.loading && valid),
  };
}
