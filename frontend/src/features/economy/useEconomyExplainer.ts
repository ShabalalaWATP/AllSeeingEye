import { useCallback, useState } from 'react';

import type { ApiError } from '@/lib/api/errors';
import { asApiError } from '@/lib/api/errors';
import {
  fetchEconomyExplainer,
  refreshEconomyExplainer,
  type EconomyExplainer,
} from '@/lib/api/economyExplainer';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';

export interface EconomyExplainerState {
  data: EconomyExplainer | null;
  loading: boolean;
  error: ApiError | null;
  refreshing: boolean;
  refreshError: ApiError | null;
  isAdmin: boolean;
  reload: () => Promise<void>;
  forceRefresh: () => Promise<void>;
}

/** One shared cached explainer per reader; only administrators may force a rewrite. */
export function useEconomyExplainer(): EconomyExplainerState {
  const resource = useScopedResource(fetchEconomyExplainer);
  const isAdmin = useAuthStore(selectIsAdmin);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<ApiError | null>(null);
  const { setData } = resource;
  const forceRefresh = useCallback(async () => {
    setRefreshing(true);
    setRefreshError(null);
    try {
      setData(await refreshEconomyExplainer());
    } catch (error) {
      setRefreshError(asApiError(error));
    } finally {
      setRefreshing(false);
    }
  }, [setData]);
  return {
    data: resource.data,
    loading: resource.loading,
    error: resource.error,
    refreshing,
    refreshError,
    isAdmin,
    reload: resource.reload,
    forceRefresh,
  };
}
