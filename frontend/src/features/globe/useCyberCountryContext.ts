import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { fetchEvents } from '@/lib/api/events';
import { describeError } from '@/lib/api/errors';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { filterByWindow } from '@/stores/events';
import { useCyberFilters } from './useCyberFilters';
import { cyberCountryGroups } from './cyberCountryContext';
import { locationQuality, type LocationQualityFilter } from './geographicPrecision';

const EMPTY: LiveEvent[] = [];
export const CYBER_CONTEXT_LIMIT = 500;
export const CYBER_REFRESH_MS = 60_000;

interface Snapshot {
  scope: string;
  events: LiveEvent[];
  fetchedAt: string;
  error: string | null;
}

/** Bounded country context stays separate from the exact viewport event mirror. */
export function useCyberCountryContext(
  enabled: boolean,
  countries: Record<string, Country>,
  country: string | null,
  windowHours: number | null,
  now: number,
  quality: LocationQualityFilter,
) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = JSON.stringify([actor, revision, enabled, country, windowHours]);
  const request = useScopedRequest();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedIso, setSelectedIso] = useState<string | null>(null);
  const showCountries = useCyberFiltersStore((state) => state.countryContext);
  if (snapshot && snapshot.scope !== scope) setSnapshot(null);
  useEffect(() => {
    const discard = () => {
      setSnapshot(null);
      setSelectedIso(null);
      setRefreshKey((value) => value + 1);
    };
    const offAuth = useAuthStore.subscribe((next, previous) => {
      if (
        next.status !== previous.status ||
        next.user?.id !== previous.user?.id ||
        next.user?.role !== previous.user?.role ||
        next.user?.is_active !== previous.user?.is_active
      )
        discard();
    });
    const offAccess = subscribeWorkspaceAccess(discard);
    return () => {
      offAuth();
      offAccess();
    };
  }, []);
  useEffect(() => {
    if (!enabled || !actor.startsWith('authenticated:') || !actor.endsWith(':true')) return;
    const signal = request();
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    void fetchEvents(
      {
        categories: ['cyber'],
        limit: CYBER_CONTEXT_LIMIT,
        ...(country ? { country } : {}),
        ...(windowHours === null
          ? {}
          : { since: new Date(Date.now() - windowHours * 3_600_000).toISOString() }),
      },
      signal,
    )
      .then((events) => {
        if (!signal.aborted)
          setSnapshot({
            scope,
            events: events.slice(0, CYBER_CONTEXT_LIMIT),
            fetchedAt: new Date().toISOString(),
            error: null,
          });
      })
      .catch((error: unknown) => {
        if (!signal.aborted)
          setSnapshot({
            scope,
            events: [],
            fetchedAt: new Date().toISOString(),
            error: describeError(error),
          });
      })
      .finally(() => {
        // Feeds may still be warming when the layer first opens. Refresh only
        // after completion, with no overlapping requests or viewport dependency.
        if (!signal.aborted)
          refreshTimer = setTimeout(() => setRefreshKey((value) => value + 1), CYBER_REFRESH_MS);
      });
    return () => {
      clearTimeout(refreshTimer);
      request();
    };
  }, [enabled, actor, scope, country, windowHours, request, refreshKey]);
  const current = snapshot?.scope === scope ? snapshot : null;
  const events = useMemo(
    () => filterByWindow(current?.events ?? EMPTY, windowHours, now),
    [current, windowHours, now],
  );
  const refined = useCyberFilters(events);
  const filtered = useMemo(
    () =>
      refined.filter(
        (event) =>
          event.category === 'cyber' && (quality === 'all' || locationQuality(event) === quality),
      ),
    [refined, quality],
  );
  const groups = useMemo(
    () => (enabled && showCountries ? cyberCountryGroups(filtered, countries) : []),
    [enabled, showCountries, filtered, countries],
  );
  const selected = groups.find((group) => group.country.iso2 === selectedIso) ?? null;
  if (selectedIso && !selected) setSelectedIso(null);
  const close = useCallback(() => setSelectedIso(null), []);
  const select = useCallback((iso: string) => setSelectedIso(iso), []);
  const refresh = useCallback(() => {
    setSnapshot(null);
    setRefreshKey((value) => value + 1);
  }, []);
  return {
    events: filtered,
    groups,
    selected,
    close,
    select,
    refresh,
    loading: enabled && actor.startsWith('authenticated:') && !current,
    fetchedAt: current?.fetchedAt ?? null,
    error: current?.error ?? null,
    limited: (current?.events.length ?? 0) >= CYBER_CONTEXT_LIMIT,
  };
}
