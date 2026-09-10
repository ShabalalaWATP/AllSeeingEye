import { useEffect, useState } from 'react';
import { RfElevationCache } from '@/lib/map/rfElevationCache';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

/** A panel-local cache; role/account/access changes clear it before React can batch renders. */
export function useRfTerrainCache() {
  const [cache] = useState(() => new RfElevationCache());
  useEffect(() => {
    const offAuth = useAuthStore.subscribe((state, previous) => {
      if (
        state.status !== previous.status ||
        state.user?.id !== previous.user?.id ||
        state.user?.role !== previous.user?.role ||
        state.user?.is_active !== previous.user?.is_active
      )
        cache.clear();
    });
    const offAccess = subscribeWorkspaceAccess(() => cache.clear());
    return () => {
      offAuth();
      offAccess();
      cache.clear();
    };
  }, [cache]);
  return cache;
}
