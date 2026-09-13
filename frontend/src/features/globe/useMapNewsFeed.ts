import { useCallback, useEffect } from 'react';
import { fetchEvents } from '@/lib/api/events';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';
import { NEWS_CATEGORIES } from './newsFilters';

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
  useEffect(
    () => () => {
      begin();
    },
    [begin, country, windowHours, active, map],
  );
  const load = useCallback(async () => {
    const asOf = Date.now();
    if (!active) return { items: [], fetchedAt: new Date(asOf).toISOString() };
    const items = await fetchEvents(
      {
        categories: NEWS_CATEGORIES,
        limit: 300,
        ...(map ? { sampling: 'geographic' as const, timeBasis: 'map_record_time' as const } : {}),
        ...(country ? { country } : {}),
        ...(windowHours !== null
          ? { since: new Date(asOf - windowHours * 3_600_000).toISOString() }
          : {}),
      },
      begin(),
    );
    return { items: items.slice(0, 300), fetchedAt: new Date(asOf).toISOString() };
  }, [begin, country, windowHours, active, map]);
  const snapshot = useScopedResource(load);
  const { loading, data, error, refresh } = snapshot;
  useEffect(() => {
    if (!active || !map || loading) return;
    const timer = setTimeout(() => void refresh(), 60_000);
    return () => clearTimeout(timer);
  }, [active, map, loading, data, error, refresh]);
  return snapshot;
}
