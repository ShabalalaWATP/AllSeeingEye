import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { SetStateAction } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

function identity() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
}

/** The key a load started now would carry; it differs from `key` once access has changed. */
export function currentScopeKey(): string {
  return `${identity()}:${workspaceRevision()}`;
}

interface Snapshot<T> {
  key: string;
  loader: () => Promise<T>;
  data: T | null;
  error: ApiError | null;
  loading: boolean;
}

/** Identity/access changes hide previous data before a fresh request can settle. */
export function useScopedResource<T>(loader: () => Promise<T>) {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const actor = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
  const key = `${actor}:${revision}`;
  const sequence = useRef(0);
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({
    key,
    loader,
    data: null,
    error: null,
    loading: true,
  });
  const load = useCallback(
    async (background: boolean) => {
      const request = ++sequence.current;
      setSnapshot((previous) =>
        background && previous.key === key && previous.loader === loader && previous.data !== null
          ? previous
          : { key, loader, data: null, error: null, loading: true },
      );
      const current = () =>
        request === sequence.current && identity() === actor && workspaceRevision() === revision;
      try {
        const data = await loader();
        if (current()) setSnapshot({ key, loader, data, error: null, loading: false });
      } catch (error) {
        if (current())
          setSnapshot({ key, loader, data: null, error: asApiError(error), loading: false });
      }
    },
    [actor, key, loader, revision],
  );
  const reload = useCallback(() => load(false), [load]);
  const refresh = useCallback(() => load(true), [load]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
    return () => {
      sequence.current += 1;
    };
  }, [reload]);
  const setData = useCallback(
    (update: SetStateAction<T | null>) => {
      if (identity() !== actor || workspaceRevision() !== revision) return;
      setSnapshot((previous) =>
        previous.loader !== loader
          ? previous
          : {
              ...previous,
              data:
                typeof update === 'function'
                  ? (update as (value: T | null) => T | null)(
                      previous.key === key ? previous.data : null,
                    )
                  : update,
            },
      );
    },
    [actor, key, loader, revision],
  );
  return {
    ...(snapshot.key === key && snapshot.loader === loader
      ? snapshot
      : { data: null, error: null, loading: true }),
    reload,
    refresh,
    setData,
    key,
  };
}
