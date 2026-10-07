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
  loader: (signal: AbortSignal) => Promise<T>;
  data: T | null;
  error: ApiError | null;
  loading: boolean;
}

/**
 * Identity/access changes hide previous data before a fresh request can settle.
 * `reload` starts again from a loading state, for explicit Retry buttons. `refresh` is a
 * background load: it keeps what is on screen (data or error) for the same scope and, if
 * it fails, keeps the previous data and reports only the error.
 */
export function useScopedResource<T>(loader: () => Promise<T>) {
  // The loader keeps its own call shape: many loaders take optional, non-signal arguments.
  const unsignalled = useCallback(() => loader(), [loader]);
  return useScopedLoads(unsignalled).resource;
}

/**
 * A scoped resource whose loader receives an abort signal and must forward it. A newer load,
 * a scope change or unmount aborts the request in flight, as does the signal passed to
 * `refreshWithSignal`; an aborted load never updates state or surfaces as an error.
 */
export function useAbortableScopedResource<T>(loader: (signal: AbortSignal) => Promise<T>) {
  const { resource, refreshWithSignal } = useScopedLoads(loader);
  return { ...resource, refreshWithSignal };
}

function useScopedLoads<T>(loader: (signal: AbortSignal) => Promise<T>) {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const actor = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
  const key = `${actor}:${revision}`;
  const sequence = useRef(0);
  const inFlight = useRef<AbortController | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({
    key,
    loader,
    data: null,
    error: null,
    loading: true,
  });
  const load = useCallback(
    async (background: boolean, external?: AbortSignal) => {
      const request = ++sequence.current;
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      const abort = () => controller.abort();
      if (external?.aborted) abort();
      external?.addEventListener('abort', abort, { once: true });
      const keeps = (previous: Snapshot<T>) =>
        background && previous.key === key && previous.loader === loader && !previous.loading;
      setSnapshot((previous) =>
        keeps(previous) ? previous : { key, loader, data: null, error: null, loading: true },
      );
      const current = () =>
        !controller.signal.aborted &&
        request === sequence.current &&
        identity() === actor &&
        workspaceRevision() === revision;
      try {
        const data = await loader(controller.signal);
        if (current()) setSnapshot({ key, loader, data, error: null, loading: false });
      } catch (error) {
        if (current())
          setSnapshot((previous) => ({
            key,
            loader,
            data: keeps(previous) ? previous.data : null,
            error: asApiError(error),
            loading: false,
          }));
      } finally {
        external?.removeEventListener('abort', abort);
        if (inFlight.current === controller) inFlight.current = null;
      }
    },
    [actor, key, loader, revision],
  );
  const reload = useCallback(() => load(false), [load]);
  const refresh = useCallback(() => load(true), [load]);
  /** A background refresh that is also aborted when `signal` is, for pollers. */
  const refreshWithSignal = useCallback((signal: AbortSignal) => load(true, signal), [load]);
  useEffect(() => {
    void reload();
    return () => {
      sequence.current += 1;
      inFlight.current?.abort();
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
  const resource = {
    ...(snapshot.key === key && snapshot.loader === loader
      ? snapshot
      : { data: null, error: null, loading: true }),
    reload,
    refresh,
    setData,
    key,
  };
  return { resource, refreshWithSignal };
}
