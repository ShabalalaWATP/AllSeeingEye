import { useCallback } from 'react';
import { fetchEvents } from '@/lib/api/events';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { NEWS_CATEGORIES } from './newsFilters';

/** A panel-only snapshot keeps unlocated headlines usable without adding map markers. */
export function useMapNewsFeed(country: string | null, windowHours: number | null) {
  const begin = useScopedRequest();
  const load = useCallback(async () => {
    const asOf = Date.now();
    const items = await fetchEvents(
      {
        categories: NEWS_CATEGORIES,
        limit: 300,
        ...(country ? { country } : {}),
        ...(windowHours !== null
          ? { since: new Date(asOf - windowHours * 3_600_000).toISOString() }
          : {}),
      },
      begin(),
    );
    return { items: items.slice(0, 300), fetchedAt: new Date(asOf).toISOString() };
  }, [begin, country, windowHours]);
  return useScopedResource(load);
}
