import { useCallback, useDeferredValue, useMemo, useState } from 'react';
import { useNow } from '@/lib/hooks/useNow';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  filterSatellites,
  isSatellite,
  isCurrentSatellitePosition,
  type SatelliteGroup,
} from '@/lib/satellites';
import { matchesSatelliteSearch, SATELLITE_QUERY_LIMIT } from './satelliteSearch';

export function useSatelliteFilters(events: LiveEvent[]) {
  const now = useNow();
  const [group, setGroup] = useState<SatelliteGroup>('all');
  const [query, updateQuery] = useState('');
  const setQuery = useCallback(
    (value: string) => updateQuery(value.slice(0, SATELLITE_QUERY_LIMIT)),
    [],
  );
  const search = query.trim().toLocaleLowerCase('en-GB');
  const deferredSearch = useDeferredValue(search);
  const terms = useMemo(
    () => (deferredSearch ? deferredSearch.split(/\s+/) : []),
    [deferredSearch],
  );
  // Stable membership avoids rebuilding all GPU layers on an unrelated clock tick.
  const membership = events
    .map((event) => (!isSatellite(event) || isCurrentSatellitePosition(event, now) ? '1' : '0'))
    .join('');
  const current = useMemo(
    () =>
      membership.includes('0') ? events.filter((_, index) => membership[index] === '1') : events,
    [events, membership],
  );
  const grouped = useMemo(() => filterSatellites(current, group), [current, group]);
  const filtered = useMemo(
    () =>
      terms.length
        ? grouped.filter((event) => !isSatellite(event) || matchesSatelliteSearch(event, terms))
        : grouped,
    [grouped, terms],
  );
  const results = useMemo(() => filtered.filter(isSatellite), [filtered]);
  const counts = useMemo(
    () =>
      Object.fromEntries(
        (['all', 'crewed', 'military', 'skynet'] as const).map((item) => [
          item,
          filterSatellites(current, item).filter(isSatellite).length,
        ]),
      ) as Record<SatelliteGroup, number>,
    [current],
  );
  return {
    filtered,
    group,
    setGroup,
    counts,
    query,
    setQuery,
    results,
    searching: search !== deferredSearch,
  };
}
