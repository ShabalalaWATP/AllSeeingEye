/**
 * The live map's collection-plan filter: one selected readable plan and its latest bounded
 * match sample. Session memory only; never persisted or published to the shared stream.
 * Any change of account or workspace access clears the selection and the private results.
 */
import { create } from 'zustand';

import type { PlanMapMatches } from '@/lib/api/direction';
import { isApiError } from '@/lib/api/errors';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from './auth';

export type PlanMatchStatus = 'idle' | 'loading' | 'ready' | 'unavailable' | 'lost' | 'failed';

interface PlanMapFilter {
  /** Account and workspace authority the current selection and results belong to. */
  authority: string;
  planId: string | null;
  status: PlanMatchStatus;
  result: PlanMapMatches | null;
  codes: ReadonlyMap<string, readonly string[]> | null;
  fetchedAt: number | null;
  message: string | null;
  /** Bumped by an explicit refresh so the loader runs again at once. */
  refreshes: number;
  select: (planId: string | null) => void;
  refresh: () => void;
  begin: (planId: string) => void;
  succeed: (planId: string, result: PlanMapMatches, at: number) => void;
  fail: (planId: string, error: unknown) => void;
  reset: () => void;
}

export function planFilterAuthority(): string {
  const { status, user } = useAuthStore.getState();
  return `${status}:${user?.id}:${user?.role}:${user?.is_active}:${workspaceRevision()}`;
}

const cleared = {
  planId: null,
  status: 'idle' as const,
  result: null,
  codes: null,
  fetchedAt: null,
  message: null,
};

export const usePlanMapFilterStore = create<PlanMapFilter>()((set, get) => {
  /** A late response for another plan or an earlier authority is discarded. */
  const current = (planId: string) =>
    get().planId === planId && get().authority === planFilterAuthority();
  return {
    authority: planFilterAuthority(),
    refreshes: 0,
    ...cleared,
    select: (planId) =>
      set({
        ...cleared,
        authority: planFilterAuthority(),
        planId,
        status: planId === null ? 'idle' : 'loading',
      }),
    refresh: () => set((state) => ({ refreshes: state.refreshes + 1 })),
    begin: (planId) => {
      if (current(planId) && get().result === null) set({ status: 'loading', message: null });
    },
    succeed: (planId, result, at) => {
      if (!current(planId) || result.plan.id !== planId) return;
      const codes = new Map(result.matches.map((match) => [match.event_id, match.codes]));
      set({ status: 'ready', result, codes, fetchedAt: at, message: null });
    },
    fail: (planId, error) => {
      if (!current(planId)) return;
      const status = isApiError(error) ? error.status : 0;
      if (status === 403 || status === 404) {
        // Lost access: drop the selection and every private result, keep only the notice.
        set({
          ...cleared,
          status: 'lost',
          message: 'This plan is no longer available to you, so its map filter was removed.',
        });
        return;
      }
      const message = isApiError(error) ? error.message : 'The plan matches could not be loaded.';
      const unavailable = status === 422 || status === 429 || status === 503;
      set({ status: unavailable ? 'unavailable' : 'failed', message });
    },
    reset: () => set({ ...cleared, authority: planFilterAuthority() }),
  };
});

useAuthStore.subscribe((next, previous) => {
  if (
    next.status !== previous.status ||
    next.user?.id !== previous.user?.id ||
    next.user?.role !== previous.user?.role ||
    next.user?.is_active !== previous.user?.is_active
  )
    usePlanMapFilterStore.getState().reset();
});
subscribeWorkspaceAccess(() => usePlanMapFilterStore.getState().reset());
