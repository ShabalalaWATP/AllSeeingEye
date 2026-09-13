import { useEffect } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { filterMapWindow } from '@/lib/newsMapTime';
import { isNewsCategory, matchesNews } from './newsFilters';
import type { NewsOptions } from './newsFilters';
import { isMappedEvent, locationQuality, type LocationQualityFilter } from './geographicPrecision';

/** Keep explicitly inspected reporting inside the current news and publication scope. */
export function useNewsSelectionGuard(
  context: { event: LiveEvent | null; close: () => void },
  scope: {
    news: { options: NewsOptions; enabled: boolean };
    quality: { filter: LocationQualityFilter };
    windowHours: number | null;
  },
  now: number,
) {
  const { options, enabled } = scope.news;
  const quality = scope.quality.filter;
  const windowHours = scope.windowHours;
  const { event, close } = context;
  useEffect(() => {
    if (
      event &&
      isNewsCategory(event.category) &&
      ((!enabled && (isMappedEvent(event) || event.geo_confidence === 'country')) ||
        (quality !== 'all' && locationQuality(event) !== quality) ||
        !matchesNews(event, options) ||
        !filterMapWindow([event], windowHours, now).length)
    )
      close();
  }, [event, close, options, windowHours, now, enabled, quality]);
}
