import type { ComponentProps } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { NewsPanel } from './NewsPanel';
import { isMappedEvent } from './geographicPrecision';
import { isNewsCategory } from './newsFilters';

/** Derive the map summary only for the mounted drawer, from its current filtered scope. */
export function NewsMapContent({
  mapEvents,
  loading,
  error,
  ...props
}: Omit<ComponentProps<typeof NewsPanel>, 'mapStatus'> & {
  mapEvents: readonly LiveEvent[];
  loading: boolean;
  error: unknown;
}) {
  const counts = {
    mapped: mapEvents.filter((event) => isNewsCategory(event.category) && isMappedEvent(event))
      .length,
    countries: new Set(
      mapEvents
        .filter(
          (event) =>
            isNewsCategory(event.category) &&
            event.geo_confidence === 'country' &&
            event.country_iso,
        )
        .map((event) => event.country_iso),
    ).size,
  };
  return <NewsPanel {...props} mapStatus={{ loading, error, ...counts }} />;
}
