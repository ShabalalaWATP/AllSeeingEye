/** Shared authority observations and polling for pages showing scoped records. */
import { isApiError } from './api/errors';
import { getTeam, listTeams } from './api/teams';
import type { TeamDetail } from './api/teams';
import { invalidateWorkspaceAccess, workspaceRevision } from './workspaceAccess';
import { useAuthStore } from '@/stores/auth';

let identityGeneration = 0;
let observed: string | undefined;
let pending: { key: string; promise: Promise<TeamDetail[]> } | undefined;

// A logout/login cycle must not reuse observations or requests from the former session.
useAuthStore.subscribe((state, previous) => {
  const user = state.user;
  const before = previous.user;
  if (
    user?.id !== before?.id ||
    user?.role !== before?.role ||
    user?.is_active !== before?.is_active
  ) {
    identityGeneration += 1;
    observed = undefined;
    pending = undefined;
  }
});

async function readWorkspaces(): Promise<TeamDetail[]> {
  const teams = (await listTeams()).filter((team) => team.is_active);
  const details: TeamDetail[] = [];
  // Bound concurrent reads; denied or archived teams cannot establish authority.
  for (let index = 0; index < teams.length; index += 4) {
    const batch = await Promise.allSettled(
      teams.slice(index, index + 4).map((team) => getTeam(team.id)),
    );
    for (const item of batch) {
      if (item.status === 'fulfilled') {
        if (item.value.team.is_active) details.push(item.value);
      } else if (!isApiError(item.reason) || ![403, 404].includes(item.reason.status)) {
        throw item.reason;
      }
    }
  }
  return details;
}

/** Compare effective authority, excluding names and other members' profile changes. */
export function loadWorkspaces(): Promise<TeamDetail[]> {
  const generation = identityGeneration;
  const revision = workspaceRevision();
  const key = `${generation}:${revision}`;
  if (pending?.key === key) return pending.promise;
  const user = useAuthStore.getState().user;
  const observe = (fingerprint: string) => {
    if (generation !== identityGeneration || revision !== workspaceRevision()) return;
    const changed = observed !== undefined && observed !== fingerprint;
    observed = fingerprint;
    // Store first, so the resulting resource reload cannot repeatedly invalidate itself.
    if (changed) invalidateWorkspaceAccess();
  };
  const promise = readWorkspaces()
    .then((details) => {
      const authority = details.flatMap((detail) => {
        if (user?.role === 'admin') return [detail.team.id];
        const member = detail.members.find((item) => item.user_id === user?.id && item.is_active);
        return member ? [`${detail.team.id}:${member.role}:${member.account_role}`] : [];
      });
      observe(JSON.stringify(authority.sort()));
      return details;
    })
    .catch((error: unknown) => {
      if (isApiError(error) && [403, 404].includes(error.status)) observe('denied');
      throw error;
    })
    .finally(() => {
      if (pending?.promise === promise) pending = undefined;
    });
  pending = { key, promise };
  return promise;
}

const refreshListeners = new Set<() => void>();
let timer: number | undefined;
const refreshAll = () => {
  for (const listener of refreshListeners) listener();
};

/** One focus listener and timer serve all mounted workspace consumers. */
export function subscribeWorkspaceRefresh(listener: () => void) {
  refreshListeners.add(listener);
  if (refreshListeners.size === 1) {
    window.addEventListener('focus', refreshAll);
    timer = window.setInterval(refreshAll, 60_000);
  }
  return () => {
    refreshListeners.delete(listener);
    if (refreshListeners.size === 0) {
      window.removeEventListener('focus', refreshAll);
      window.clearInterval(timer);
      timer = undefined;
    }
  };
}
