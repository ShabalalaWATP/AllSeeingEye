import { useMemo } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { matchesCyberFilters } from '@/lib/cyber';
import { useCyberFiltersStore } from '@/stores/cyberFilters';

export function useCyberFilters(events: readonly LiveEvent[]) {
  const kind = useCyberFiltersStore((state) => state.kind);
  const query = useCyberFiltersStore((state) => state.query);
  return useMemo(
    () => events.filter((event) => matchesCyberFilters(event, kind, query)),
    [events, kind, query],
  );
}
