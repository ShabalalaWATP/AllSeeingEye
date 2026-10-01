import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { OWNERSHIP_PARAM, parseOwnershipScope } from '@/lib/ownershipScope';
import type { OwnershipScope } from '@/lib/ownershipScope';
import { useAuthStore } from '@/stores/auth';

/**
 * The list scope held in the address (`?scope=all`), so an administrator's wider view is a
 * shareable, visible choice. Other roles always read "mine", whatever the address says.
 */
export function useOwnershipScope() {
  const [params, setParams] = useSearchParams();
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';
  const scope = parseOwnershipScope(params.get(OWNERSHIP_PARAM), isAdmin);
  const setScope = useCallback(
    (next: OwnershipScope) =>
      setParams(
        (previous) => {
          const updated = new URLSearchParams(previous);
          if (next === 'all') updated.set(OWNERSHIP_PARAM, 'all');
          else updated.delete(OWNERSHIP_PARAM);
          return updated;
        },
        { replace: true },
      ),
    [setParams],
  );
  return { scope, setScope, isAdmin, viewerId: user?.id };
}

export type OwnershipScopeState = ReturnType<typeof useOwnershipScope>;
