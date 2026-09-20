import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import type { EventsState } from './events';

/** Events inside the nation filter, before category switches apply. */
export function filterByCountry(events: LiveEvent[], country: string | null): LiveEvent[] {
  return country === null ? events : events.filter((event) => event.country_iso === country);
}

/** Events published within the window ending now; null keeps everything retained. */
export function filterByWindow(
  events: LiveEvent[],
  hours: number | null,
  now: number,
): LiveEvent[] {
  if (hours === null) return events;
  const since = now - hours * 3_600_000;
  return events.filter(
    (event) => event.published_at !== null && Date.parse(event.published_at) >= since,
  );
}

export const selectCountryEvents = (state: EventsState): LiveEvent[] =>
  filterByCountry(state.list, state.country);

export const selectVisibleEvents = (state: EventsState): LiveEvent[] => {
  const scoped = selectCountryEvents(state);
  return state.hidden.length === 0
    ? scoped
    : scoped.filter((event) => !state.hidden.includes(event.category));
};

export const selectSelectedEvent = (state: EventsState): LiveEvent | null =>
  state.selectedId === null ? null : (state.byId[state.selectedId] ?? null);

export function countByCategory(events: readonly LiveEvent[]): Partial<Record<Category, number>> {
  const counts: Partial<Record<Category, number>> = {};
  for (const event of events) counts[event.category] = (counts[event.category] ?? 0) + 1;
  return counts;
}
