import { useEffect, useMemo } from 'react';
import { countByCategory, filterByCountry, filterByWindow, useEventsStore } from '@/stores/events';
import { useObservationFilters } from './ObservationControls';
import { useSatelliteFilters } from './useSatelliteFilters';
import { useHazardFilters } from './useHazardFilters';
import { useConflictFilters } from './useConflictFilters';
import { useLocationQuality } from './useLocationQuality';
import { useCyberFilters } from './useCyberFilters';

/** One event-scope pipeline for map symbols, lists, counts and selected details. */
export function useDashboardEvents(now: number) {
  const hidden = useEventsStore((state) => state.hidden);
  const country = useEventsStore((state) => state.country);
  const requestedId = useEventsStore((state) => state.selectedId);
  const stats = useEventsStore((state) => state.stats);
  const status = useEventsStore((state) => state.status);
  const error = useEventsStore((state) => state.error);
  const select = useEventsStore((state) => state.select);
  const setCountry = useEventsStore((state) => state.setCountry);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const list = useEventsStore((state) => state.list);
  const windowHours = useEventsStore((state) => state.windowHours);
  const setWindow = useEventsStore((state) => state.setWindow);
  const coverageBounds = useEventsStore((state) => state.coverageBounds);
  const countryEvents = useMemo(() => filterByCountry(list, country), [list, country]);
  const scoped = useMemo(
    () => filterByWindow(countryEvents, windowHours, now),
    [countryEvents, windowHours, now],
  );
  const counts = useMemo(() => countByCategory(scoped), [scoped]);
  const observations = useObservationFilters(scoped);
  const satellites = useSatelliteFilters(observations.filtered);
  const hazards = useHazardFilters(satellites.filtered);
  const conflicts = useConflictFilters(hazards.filtered);
  const cyberFiltered = useCyberFilters(conflicts.filtered);
  const quality = useLocationQuality(cyberFiltered, hidden);
  // Unplotted records remain inspectable. Selection follows filtered membership,
  // not whether the record has coordinates. Invalid selections cannot revive later.
  const selected = quality.filtered.find((event) => event.id === requestedId) ?? null;
  useEffect(() => {
    if (requestedId && !selected && useEventsStore.getState().selectedId === requestedId)
      select(null);
  }, [requestedId, selected, select]);
  const storySize = useMemo(
    () =>
      selected?.story_id == null
        ? 1
        : list.filter((event) => event.story_id === selected.story_id).length,
    [list, selected],
  );
  return {
    hidden,
    country,
    selectedId: selected?.id ?? null,
    selected,
    stats,
    status,
    error,
    select,
    setCountry,
    toggleCategory,
    list,
    windowHours,
    setWindow,
    coverageBounds,
    scoped,
    counts,
    observations,
    satellites,
    hazards,
    conflicts,
    quality,
    storySize,
  };
}
