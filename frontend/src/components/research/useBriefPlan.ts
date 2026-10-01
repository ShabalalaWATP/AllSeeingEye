import { useCallback } from 'react';

import { fetchPlan } from '@/lib/api/direction';
import type { CollectionPlan } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

/** Why research cannot start from this plan yet, or null when the reviewed plan is usable. */
export function planBlocker(
  plan: CollectionPlan | null,
  error: ApiError | null,
  teamId: string | null,
): string | null {
  if (error !== null)
    return error.status === 404 || error.status === 403
      ? 'This collection plan no longer exists or is not available to you. Remove it from the brief or open the assessment again from a plan you can read.'
      : `The collection plan could not be loaded. ${describeError(error)}`;
  if (plan === null) return 'Loading the collection plan before research can start.';
  if ((plan.team_id ?? null) !== teamId)
    return 'This brief and its collection plan belong to different workspaces. Start the assessment again from the plan.';
  if (!plan.enabled)
    return 'This collection plan is disabled. Enable it in Plans and areas before starting research.';
  return null;
}

/**
 * The plan a brief names, loaded from the server by id. Its requirements never travel in the
 * URL or browser storage, and access changes discard the loaded copy.
 */
export function useBriefPlan(planId: string | null, teamId: string | null) {
  const loader = useCallback(
    async () => (planId === null ? null : await fetchPlan(planId)),
    [planId],
  );
  const resource = useScopedResource(loader);
  const plan = planId === null ? null : resource.data;
  return {
    plan,
    loading: resource.loading,
    error: resource.error,
    reload: resource.refresh,
    blocker: planId === null ? null : planBlocker(plan, resource.error, teamId),
  };
}

export type BriefPlan = ReturnType<typeof useBriefPlan>;
