import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { fetchEvents } from '@/lib/api/events';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';
import { isNewsCategory, NEWS_CATEGORIES } from './newsFilters';
import { LiveEventSnapshot } from '@/lib/liveEventSnapshot';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { subscribeEventChanges } from '@/stores/events.changes';
import { useEventsStore } from '@/stores/events';

function identity(state = useAuthStore.getState()) {
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`;
}

/** Bounded snapshots can serve the visible map or the on-demand headline panel. */
export function useMapNewsFeed(
  country: string | null,
  windowHours: number | null,
  enabled = true,
  map = false,
) {
  const authenticated = useAuthStore(
    (state) => state.status === 'authenticated' && state.user?.is_active === true,
  );
  const active = enabled && authenticated;
  const begin = useScopedRequest();
  const actor = useAuthStore(identity);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const [generation, setGeneration] = useState(0);
  const reconciler = useMemo(
    () =>
      new LiveEventSnapshot(
        (event) => isNewsCategory(event.category) && (!country || event.country_iso === country),
      ),
    // Every authority/query transition needs a fresh journal, even with the same country.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actor, revision, generation, country, windowHours, active, map],
  );
  const items = useSyncExternalStore(reconciler.subscribe, reconciler.getSnapshot);
  useEffect(() => {
    const clear = () => {
      reconciler.clear();
      setGeneration((value) => value + 1);
    };
    const offEvents = subscribeEventChanges((change) => {
      if (change.kind === 'reset') clear();
      else if (change.kind === 'upsert') reconciler.upsert(change.events);
      else reconciler.expire(change.ids);
    });
    const offAuth = useAuthStore.subscribe(() => {
      if (identity() !== actor) clear();
    });
    return () => {
      offEvents();
      offAuth();
      reconciler.clear();
    };
  }, [reconciler, actor]);
  useEffect(
    () => () => {
      begin();
    },
    [begin, country, windowHours, active, map],
  );
  const load = useCallback(async () => {
    const asOf = Date.now();
    if (!active) return { fetchedAt: new Date(asOf).toISOString() };
    const signal = begin();
    const pending = reconciler.begin(useEventsStore.getState().list);
    try {
      const received = await fetchEvents(
        {
          categories: NEWS_CATEGORIES,
          limit: 300,
          ...(map
            ? { sampling: 'geographic' as const, timeBasis: 'map_record_time' as const }
            : {}),
          ...(country ? { country } : {}),
          ...(windowHours !== null
            ? { since: new Date(asOf - windowHours * 3_600_000).toISOString() }
            : {}),
        },
        signal,
      );
      signal.throwIfAborted();
      reconciler.finish(pending, received);
      return { fetchedAt: new Date(asOf).toISOString() };
    } finally {
      reconciler.cancel(pending);
    }
  }, [begin, country, windowHours, active, map, reconciler]);
  const snapshot = useScopedResource(load);
  const { loading, data, error, refresh } = snapshot;
  useEffect(() => {
    if (!active || !map || loading) return;
    const timer = setTimeout(() => void refresh(), 60_000);
    return () => clearTimeout(timer);
  }, [active, map, loading, data, error, refresh]);
  const reconciled = useMemo(() => (data ? { ...data, items } : null), [data, items]);
  return { ...snapshot, data: reconciled };
}
