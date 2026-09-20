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
export function useContextEvents(
  sources: readonly string[],
  country?: string | null,
  enabled = true,
) {
  const auth = useAuthStore(actor);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = JSON.stringify([auth, revision, sources, country, enabled]);
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
    if (!enabled || !auth.startsWith('authenticated:')) return;
    const signal = request();
    const cancelled = () => signal.aborted;
    // Separate capped reads prevent a busy bulletin source from hiding singleton indices.
    const limit = Math.max(1, Math.floor(100 / sources.length));
    const load = async () => {
      const events: LiveEvent[] = [];
      let failures = 0;
      // The server admits two reads per user. Leave one slot for another map panel.
      for (const source of sources) {
        if (cancelled()) return;
        try {
          const result = await fetchEvents(
            { sources: [source], limit, ...(country ? { country } : {}) },
            signal,
          );
          if (cancelled()) return;
          events.push(...result.slice(0, limit));
        } catch {
          if (cancelled()) return;
          failures += 1;
        }
      }
      if (cancelled()) return;
      setSnapshot({
        scope,
        events,
        failures,
        fetchedAt: new Date().toISOString(),
      });
    };
    void load();
    return () => {
      request();
    };
  }, [auth, scope, sources, country, enabled, request, refresh]);

  const current = snapshot?.scope === scope ? snapshot : null;
  return {
    events: current?.events ?? EMPTY,
    loading: enabled && auth.startsWith('authenticated:') && !current,
    failures: current?.failures ?? 0,
    fetchedAt: current?.fetchedAt ?? null,
    refresh: () => {
      setSnapshot(null);
      setRefresh((value) => value + 1);
    },
  };
}
