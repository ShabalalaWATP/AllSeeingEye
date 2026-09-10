import { useCallback, useDeferredValue, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { trafficSearchText } from '@/lib/traffic';

export type TrafficKind = 'aircraft' | 'vessels';
export type AircraftGroundState = 'airborne' | 'ground' | 'unknown';
export type AircraftGroundFilter = 'all' | AircraftGroundState;
export interface TrafficRefinement {
  query: string;
  source: string;
  ground: AircraftGroundFilter;
}
export const TRAFFIC_QUERY_LIMIT = 100;
const searchCache = new WeakMap<LiveEvent, string>();

export function isTrafficKind(event: LiveEvent, kind: TrafficKind): boolean {
  return kind === 'aircraft'
    ? event.category === 'aviation'
    : event.category === 'maritime' && event.subtype === 'vessel_position';
}

/** Only the retained boolean is a status report. Missing and malformed values stay unknown. */
export function aircraftGroundState(event: LiveEvent): AircraftGroundState {
  return event.attributes.on_ground === true
    ? 'ground'
    : event.attributes.on_ground === false
      ? 'airborne'
      : 'unknown';
}

export function matchesTrafficRefinement(
  event: LiveEvent,
  kind: TrafficKind,
  filter?: TrafficRefinement,
): boolean {
  if (!filter || !isTrafficKind(event, kind)) return true;
  if (filter.source && event.source_id !== filter.source) return false;
  if (
    kind === 'aircraft' &&
    filter.ground !== 'all' &&
    aircraftGroundState(event) !== filter.ground
  )
    return false;
  if (!filter.query) return true;
  let text = searchCache.get(event);
  if (text === undefined) {
    text = trafficSearchText(event);
    searchCache.set(event, text);
  }
  return text.includes(filter.query);
}

/** One deferred spec is used by both the map and the popup, without extra collection work. */
export function useTrafficRefinements(events: readonly LiveEvent[], kind: TrafficKind) {
  const [query, updateQuery] = useState('');
  const [source, setSource] = useState('');
  const [ground, setGround] = useState<AircraftGroundFilter>('all');
  const setQuery = useCallback(
    (value: string) => updateQuery(value.slice(0, TRAFFIC_QUERY_LIMIT)),
    [],
  );
  const normalisedQuery = query.trim().toLowerCase();
  const deferredQuery = useDeferredValue(normalisedQuery);
  const sources = useMemo(
    () =>
      [
        ...new Set(
          events.filter((event) => isTrafficKind(event, kind)).map((event) => event.source_id),
        ),
      ].sort(),
    [events, kind],
  );
  const applied = useMemo(
    () => ({ query: deferredQuery, source, ground }),
    [deferredQuery, source, ground],
  );
  return useMemo(
    () => ({
      query,
      setQuery,
      source,
      setSource,
      ground,
      setGround,
      sources,
      applied,
      searching: normalisedQuery !== deferredQuery,
    }),
    [query, setQuery, source, ground, sources, applied, normalisedQuery, deferredQuery],
  );
}

export type TrafficRefinementsState = ReturnType<typeof useTrafficRefinements>;
