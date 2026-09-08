import { useMemo, useState } from 'react';
import { useNow } from '@/lib/hooks/useNow';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  filterSatellites,
  isSatellite,
  isCurrentSatellitePosition,
  type SatelliteGroup,
} from '@/lib/satellites';

export function useSatelliteFilters(events: LiveEvent[]) {
  const now = useNow();
  const [group, setGroup] = useState<SatelliteGroup>('all');
  // Stable membership avoids rebuilding all GPU layers on an unrelated clock tick.
  const membership = events
    .map((event) => (!isSatellite(event) || isCurrentSatellitePosition(event, now) ? '1' : '0'))
    .join('');
  const current = useMemo(
    () =>
      membership.includes('0') ? events.filter((_, index) => membership[index] === '1') : events,
    [events, membership],
  );
  const filtered = useMemo(() => filterSatellites(current, group), [current, group]);
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
  return { filtered, group, setGroup, counts };
}
