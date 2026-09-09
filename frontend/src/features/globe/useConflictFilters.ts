import { useEffect, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  countConflictReports,
  filterConflictReports,
  isHistoricalConflict,
  type ConflictGroup,
} from '@/lib/conflicts';
import {
  conflictSourceChoices,
  matchesConflictDisplay,
  type ConflictPrecision,
} from '@/lib/conflictDisplayFilters';
import { useEventsStore } from '@/stores/events';

export function useConflictFilters(events: LiveEvent[]) {
  const [group, setGroup] = useState<ConflictGroup>('all');
  const [includeHistorical, setIncludeHistorical] = useState(false);
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [precision, setPrecision] = useState<ConflictPrecision>('all');
  const sourceOptions = useMemo(() => conflictSourceChoices(events), [events]);
  const searched = useMemo(
    () => events.filter((event) => matchesConflictDisplay(event, query, source, precision)),
    [events, query, source, precision],
  );
  const scoped = useMemo(
    () => filterConflictReports(searched, 'all', includeHistorical),
    [searched, includeHistorical],
  );
  const filtered = useMemo(() => filterConflictReports(scoped, group, true), [scoped, group]);
  const counts = useMemo(() => countConflictReports(scoped), [scoped]);
  const historicalCount = useMemo(() => events.filter(isHistoricalConflict).length, [events]);
  const selectedId = useEventsStore((state) => state.selectedId);
  const select = useEventsStore((state) => state.select);
  useEffect(() => {
    const selected = events.find((event) => event.id === selectedId);
    if (selected?.category === 'conflict' && !filtered.some((event) => event.id === selected.id))
      select(null);
  }, [events, filtered, selectedId, select]);
  return {
    group,
    setGroup,
    filtered,
    counts,
    includeHistorical,
    setIncludeHistorical,
    historicalCount,
    query,
    setQuery,
    source,
    setSource,
    precision,
    setPrecision,
    sourceOptions,
  };
}
