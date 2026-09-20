import { useMemo } from 'react';
import { useDashboardSelection } from './useDashboardSelection';
import { countByCategory, filterByCountry, useEventsStore } from '@/stores/events';
import { filterMapWindow } from '@/lib/newsMapTime';
import { useObservationFilters } from './ObservationControls';
import { useSatelliteFilters } from './useSatelliteFilters';
import { useHazardFilters } from './useHazardFilters';
import { useConflictFilters } from './useConflictFilters';
import { useLocationQuality } from './useLocationQuality';
import { useCyberFilters } from './useCyberFilters';
import { useFiresFilters } from './useFiresFilters';
import { fireKind } from '@/lib/hazards';
import { isNewsCategory, useNewsFilters } from './newsFilters';
import { useMapNewsFeed } from './useMapNewsFeed';
import { usePageVisible } from '@/components/brand/useMotionPreferences';

/** One event-scope pipeline for map symbols, lists, counts and selected details. */
export function useDashboardEvents(now: number) {
  const hidden = useEventsStore((state) => state.hidden);
  const country = useEventsStore((state) => state.country);
  const stats = useEventsStore((state) => state.stats);
  const status = useEventsStore((state) => state.status);
  const error = useEventsStore((state) => state.error);
  const setCountry = useEventsStore((state) => state.setCountry);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const list = useEventsStore((state) => state.list);
  const windowHours = useEventsStore((state) => state.windowHours);
  const setWindow = useEventsStore((state) => state.setWindow);
  const coverageBounds = useEventsStore((state) => state.coverageBounds);
  const visible = usePageVisible();
  const newsSnapshot = useMapNewsFeed(
    country,
    windowHours,
    !hidden.includes('news') && visible,
    true,
  );
  const combined = useMemo(
    () => [
      ...new Map(
        [...list, ...(newsSnapshot.data?.items ?? [])].map((event) => [event.id, event]),
      ).values(),
    ],
    [list, newsSnapshot.data],
  );
  const countryEvents = useMemo(() => filterByCountry(combined, country), [combined, country]);
  const scoped = useMemo(
    () => filterMapWindow(countryEvents, windowHours, now),
    [countryEvents, windowHours, now],
  );
  const counts = useMemo(() => countByCategory(scoped), [scoped]);
  // Fires and News have independent UI ownership while keeping source categories intact.
  const categoryScope = useMemo(
    () =>
      scoped.filter(
        (event) =>
          event.category !== 'disaster' || fireKind(event) !== null || !hidden.includes('disaster'),
      ),
    [scoped, hidden],
  );
  const observations = useObservationFilters(categoryScope);
  const satellites = useSatelliteFilters(observations.filtered);
  const hazards = useHazardFilters(satellites.filtered);
  const fires = useFiresFilters(hazards.filtered);
  const news = useNewsFilters(fires.filtered, !hidden.includes('news'));
  const conflicts = useConflictFilters(news.filtered);
  const cyberFiltered = useCyberFilters(conflicts.filtered);
  const renderHidden = useMemo(
    () => hidden.filter((category) => category !== 'disaster' && !isNewsCategory(category)),
    [hidden],
  );
  const quality = useLocationQuality(cyberFiltered, renderHidden);
  const { selected, select } = useDashboardSelection(quality.filtered);
  const storySize = useMemo(
    () =>
      selected?.story_id == null
        ? 1
        : list.filter((event) => event.story_id === selected.story_id).length,
    [list, selected],
  );
  return {
    hidden,
    renderHidden,
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
    fires,
    news,
    newsSnapshot,
    conflicts,
    quality,
    storySize,
  };
}
