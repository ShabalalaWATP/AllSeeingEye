import { useCallback, useEffect } from 'react';

import { useDraftState } from '@/lib/formDrafts';
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
  /**
   * Mirrors the server's write rule (AccessPolicy.require_write): administrators write
   * anything; otherwise archived teams are read-only, creators write their own records and
   * a team's designated managers write its team records. The server stays authoritative.
   */
  const canManage = (record: { created_by: string; team_id?: string | null }) => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (!record.team_id) return record.created_by === user.id;
    const detail = teams.find((entry) => entry.team.id === record.team_id);
    if (!detail?.team.is_active) return false;
    if (record.created_by === user.id) return true;
    return detail.members.some(
      (member) => member.user_id === user.id && member.is_active && member.role === 'manager',
    );
  };
  const canAcknowledge = (teamId: string | null | undefined) =>
    Boolean(user) &&
    (user?.role === 'admin' || !teamId || teams.some((entry) => entry.team.id === teamId));
  return { ...resource, teams, label, canManage, canAcknowledge };
}

export type Workspaces = ReturnType<typeof useWorkspaces>;

/**
 * Selection cannot survive an identity or access invalidation. A form draft may keep it for
 * the same account and access state, so a restored draft returns to its own workspace.
 */
export function useWorkspaceSelection(
  workspaces: Workspaces,
  draftForm: string | null = null,
  /** A starting team, such as the source report's own, instead of Personal. */
  initial = '',
) {
  const [choice, setChoice] = useDraftState(draftForm, 'workspace', {
    key: workspaces.key,
    id: initial,
  });
  const selected = choice.key === workspaces.key ? choice.id : '';
  const valid = !selected || workspaces.teams.some((entry) => entry.team.id === selected);
  const select = useCallback(
    (id: string) => setChoice({ key: workspaces.key, id }),
    [workspaces.key, setChoice],
  );
  return {
    teamId: selected,
    select,
    valid,
    ready: selected === '' || (!workspaces.loading && valid),
  };
}
