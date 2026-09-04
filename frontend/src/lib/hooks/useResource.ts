import { useCallback, useEffect, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: Dispatch<SetStateAction<T | null>>;
}

/** Loads a value once on mount and exposes reload plus local updates. */
export function useResource<T>(loader: () => Promise<T>): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);

  // State is only touched after the request settles, so the initial load is
  // safe to start from an effect (loading already starts as true).
  const load = useCallback(async () => {
    try {
      const value = await loader();
      setData(value);
      setError(null);
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setLoading(false);
    }
  }, [loader]);

  const reload = useCallback(async () => {
    setLoading(true);
    await load();
  }, [load]);

  useEffect(() => {
    // The loader only updates state after it settles; the lint rule cannot see
    // the await. Phase 1 replaces this hook with TanStack Query for server state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { data, error, loading, reload, setData };
}
