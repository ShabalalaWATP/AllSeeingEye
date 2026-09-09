import { useEffect, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  countHazards,
  DEFAULT_HAZARD_OPTIONS,
  hazardKind,
  matchesHazard,
  matchesHazardGroup,
  type HazardOptions,
} from '@/lib/hazards';
import { useEventsStore } from '@/stores/events';

export function useHazardFilters(events: LiveEvent[]) {
  const [options, setOptions] = useState<HazardOptions>(DEFAULT_HAZARD_OPTIONS);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (options.hours === 'all') return;
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, [options.hours]);
  const updateOptions = (patch: Partial<HazardOptions>) => {
    setNow(Date.now());
    setOptions((previous) => ({ ...previous, ...patch }));
  };
  const scoped = useMemo(
    () => events.filter((event) => matchesHazard(event, { ...options, group: 'all' }, now)),
    [events, options, now],
  );
  const counts = useMemo(() => countHazards(scoped), [scoped]);
  const filtered = useMemo(
    () => scoped.filter((event) => matchesHazardGroup(event, options.group)),
    [scoped, options.group],
  );
  const selectedId = useEventsStore((state) => state.selectedId);
  const select = useEventsStore((state) => state.select);
  useEffect(() => {
    const selected = events.find((event) => event.id === selectedId);
    if (selected && hazardKind(selected) !== null && !matchesHazard(selected, options, now))
      select(null);
  }, [events, selectedId, select, options, now]);
  return { options, updateOptions, counts, filtered };
}
