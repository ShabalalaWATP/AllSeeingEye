import { useEffect, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { ConflictGroup } from '@/lib/conflicts';
import type { ConflictPrecision } from '@/lib/conflictDisplayFilters';
import { useEventsStore } from '@/stores/events';
import { deriveConflictScope } from './conflictScope';

export function useConflictFilters(events: LiveEvent[]) {
  const [group, setGroup] = useState<ConflictGroup>('all');
  const [includeHistorical, setIncludeHistorical] = useState(false);
  const [includeUnreviewed, setIncludeUnreviewed] = useState(false);
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [precision, setPrecision] = useState<ConflictPrecision>('all');
  const { filtered, counts, sourceOptions, historicalCount, unreviewedCount } = useMemo(
    () =>
      deriveConflictScope(events, {
        group,
        includeHistorical,
        includeUnreviewed,
        query,
        source,
        precision,
      }),
    [events, group, includeHistorical, includeUnreviewed, query, source, precision],
  );
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
    includeUnreviewed,
    setIncludeUnreviewed,
    unreviewedCount,
    query,
    setQuery,
    source,
    setSource,
    precision,
    setPrecision,
    sourceOptions,
  };
}
