import { useMemo, useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { locationQuality, type LocationQualityFilter } from './geographicPrecision';

/** Shared map/globe selection. No coordinates or source precision are changed. */
export function useLocationQuality(events: readonly LiveEvent[], hidden: readonly Category[]) {
  const [filter, setFilter] = useState<LocationQualityFilter>('all');
  const visible = useMemo(
    () => events.filter((event) => !hidden.includes(event.category)),
    [events, hidden],
  );
  const filtered = useMemo(
    () =>
      filter === 'all' ? visible : visible.filter((event) => locationQuality(event) === filter),
    [visible, filter],
  );
  return { visible, filtered, filter, setFilter };
}
