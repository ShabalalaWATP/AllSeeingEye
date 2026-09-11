import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { asApiError, type ApiError } from '@/lib/api/errors';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export function jobAuthority() {
  const state = useAuthStore.getState();
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}:${workspaceRevision()}`;
}
interface Snapshot<T> {
  key: string;
  loader: (signal: AbortSignal) => Promise<T>;
  data: T | null;
  error: ApiError | null;
}

/** One visible-page poll at a time. Leaving only stops observation of the server job. */
export function useJobPolling<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  shouldPoll: (data: T) => boolean,
  paused = false,
) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${actor}:${revision}`;
  const [snapshot, setSnapshot] = useState<Snapshot<T> | null>(null);
  const [reloadIndex, setReloadIndex] = useState(0);
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const replace = useCallback(
    (data: T) => {
      if (key !== jobAuthority()) return;
      generation.current++;
      pending.current?.abort();
      setSnapshot({ key, loader, data, error: null });
    },
    [key, loader],
  );

  useEffect(() => {
    const session = useAuthStore.getState();
    if (paused || session.status !== 'authenticated' || !session.user?.is_active) return;
    let disposed = false,
      terminal = false;
    let timer: number | undefined;
    const stop = () => {
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
      generation.current++;
      pending.current?.abort();
      pending.current = null;
    };
    const current = (id: number, signal: AbortSignal) =>
      !disposed && !signal.aborted && generation.current === id && jobAuthority() === key;
    const poll = async () => {
      if (disposed || terminal || document.visibilityState !== 'visible' || jobAuthority() !== key)
        return;
      const controller = new AbortController();
      pending.current = controller;
      const id = ++generation.current;
      try {
        const data = await loader(controller.signal);
        if (!current(id, controller.signal)) return;
        setSnapshot({ key, loader, data, error: null });
        terminal = !shouldPoll(data);
      } catch (caught) {
        if (!current(id, controller.signal)) return;
        const error = asApiError(caught);
        // Access failures discard the last private view and require an explicit fresh read.
        terminal = [401, 403, 404].includes(error.status);
        setSnapshot((previous) => ({
          key,
          loader,
          data:
            terminal || previous?.key !== key || previous.loader !== loader ? null : previous.data,
          error,
        }));
      } finally {
        if (pending.current === controller) pending.current = null;
        if (current(id, controller.signal) && !terminal)
          timer = window.setTimeout(() => void poll(), 3000);
      }
    };
    const visibility = () => {
      stop();
      if (document.visibilityState === 'visible') void poll();
    };
    const access = () => {
      if (jobAuthority() !== key) stop();
    };
    const offAuth = useAuthStore.subscribe(access);
    const offAccess = subscribeWorkspaceAccess(access);
    document.addEventListener('visibilitychange', visibility);
    void poll();
    return () => {
      disposed = true;
      stop();
      offAuth();
      offAccess();
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [key, loader, shouldPoll, paused, reloadIndex]);
  if (snapshot && (snapshot.key !== key || snapshot.loader !== loader)) setSnapshot(null);
  const visible = snapshot?.key === key && snapshot.loader === loader ? snapshot : null;
  return {
    data: visible?.data ?? null,
    error: visible?.error ?? null,
    loading: visible === null,
    replace,
    reload: () => setReloadIndex((value) => value + 1),
    key,
  };
}
