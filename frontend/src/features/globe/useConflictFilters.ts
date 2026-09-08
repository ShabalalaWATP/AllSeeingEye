import { useEffect, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  conflictKind,
  countConflictReports,
  filterConflictReports,
  isHistoricalConflict,
  type ConflictGroup,
} from '@/lib/conflicts';
import { useEventsStore } from '@/stores/events';

export function useConflictFilters(events: LiveEvent[]) {
  const [group, setGroup] = useState<ConflictGroup>('all');
  const [includeHistorical, setIncludeHistorical] = useState(false);
  const scoped = useMemo(
    () => filterConflictReports(events, 'all', includeHistorical),
    [events, includeHistorical],
  );
  const filtered = useMemo(() => filterConflictReports(scoped, group, true), [scoped, group]);
  const counts = useMemo(() => countConflictReports(scoped), [scoped]);
  const historicalCount = useMemo(() => events.filter(isHistoricalConflict).length, [events]);
  const selectedId = useEventsStore((state) => state.selectedId);
  const select = useEventsStore((state) => state.select);
  useEffect(() => {
    const selected = events.find((event) => event.id === selectedId);
    const kind = selected ? conflictKind(selected) : null;
    if (
      kind !== null &&
      ((group !== 'all' && kind !== group) ||
        (selected && !includeHistorical && isHistoricalConflict(selected)))
    )
      select(null);
  }, [events, group, selectedId, select, includeHistorical]);
  return {
    group,
    setGroup,
    filtered,
    counts,
    includeHistorical,
    setIncludeHistorical,
    historicalCount,
  };
}
