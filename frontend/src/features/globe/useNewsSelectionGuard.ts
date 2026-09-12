import { useEffect } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { filterByWindow } from '@/stores/events';
import { isNewsCategory, matchesNews } from './newsFilters';
import type { NewsOptions } from './newsFilters';

/** Keep explicitly inspected reporting inside the current news and publication scope. */
export function useNewsSelectionGuard({
  context,
  options,
  windowHours,
  now,
}: {
  context: { event: LiveEvent | null; close: () => void };
  options: NewsOptions;
  windowHours: number | null;
  now: number;
}) {
  const { event, close } = context;
  useEffect(() => {
    if (
      event &&
      isNewsCategory(event.category) &&
      (!matchesNews(event, options) || !filterByWindow([event], windowHours, now).length)
    )
      close();
  }, [event, close, options, windowHours, now]);
}
