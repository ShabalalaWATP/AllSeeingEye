import { useEffect, useState, useSyncExternalStore } from 'react';
import { fetchEvents } from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

const EMPTY: LiveEvent[] = [];
function actor(state: ReturnType<typeof useAuthStore.getState>) {
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`;
}

interface Snapshot {
  scope: string;
  events: LiveEvent[];
  fetchedAt: string;
  failures: number;
}

/** Mounted panels read a bounded store snapshot, never open a second stream or poll. */
export function useContextEvents(sources: readonly string[], country?: string | null) {
  const auth = useAuthStore(actor);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = JSON.stringify([auth, revision, sources, country]);
  const request = useScopedRequest();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [refresh, setRefresh] = useState(0);
  // Forget a superseded scope, so returning to it cannot revive an earlier identity's snapshot.
  if (snapshot && snapshot.scope !== scope) setSnapshot(null);

  useEffect(() => {
    const discard = () => {
      setSnapshot(null);
      setRefresh((value) => value + 1);
    };
    // Observe every authority transition, including logout and same-account login in one batch.
    const offAuth = useAuthStore.subscribe((next, previous) => {
      if (actor(next) !== actor(previous)) discard();
    });
    const offAccess = subscribeWorkspaceAccess(discard);
    return () => {
      offAuth();
      offAccess();
    };
  }, []);

  useEffect(() => {
    if (!auth.startsWith('authenticated:')) return;
    const signal = request();
    // Separate capped reads prevent a busy bulletin source from hiding singleton indices.
    const limit = Math.max(1, Math.floor(100 / sources.length));
    void Promise.allSettled(
      sources.map((source) =>
        fetchEvents({ sources: [source], limit, ...(country ? { country } : {}) }, signal),
      ),
    ).then((results) => {
      if (signal.aborted) return;
      setSnapshot({
        scope,
        events: results.flatMap((result) =>
          result.status === 'fulfilled' ? result.value.slice(0, limit) : [],
        ),
        failures: results.filter((result) => result.status === 'rejected').length,
        fetchedAt: new Date().toISOString(),
      });
    });
    return () => {
      request();
    };
  }, [auth, scope, sources, country, request, refresh]);

  const current = snapshot?.scope === scope ? snapshot : null;
  return {
    events: current?.events ?? EMPTY,
    loading: auth.startsWith('authenticated:') && !current,
    failures: current?.failures ?? 0,
    fetchedAt: current?.fetchedAt ?? null,
    refresh: () => {
      setSnapshot(null);
      setRefresh((value) => value + 1);
    },
  };
}
