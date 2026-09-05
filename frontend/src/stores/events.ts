/**
 * The browser's mirror of the live store: a bounded map of events kept current by
 * the stream, plus which categories are shown and which event is selected.
 */
import { create } from 'zustand';

import { fetchEvents, fetchStats } from '@/lib/api/events';
import { streamExpireSchema, streamUpsertSchema } from '@/lib/api/eventSchemas';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import type { SseMessage, StreamStatus } from '@/lib/sse';

export const MAX_CLIENT_EVENTS = 5_000;

export interface EventsState {
  byId: Record<string, LiveEvent>;
  list: LiveEvent[];
  hidden: Category[];
  /** ISO 3166-1 alpha-2 code of the nation filter, or null for the whole world. */
  country: string | null;
  stats: StoreStats | null;
  status: StreamStatus;
  loaded: boolean;
  error: string | null;
  selectedId: string | null;
  load: () => Promise<void>;
  applyUpsert: (events: LiveEvent[]) => void;
  applyExpire: (ids: string[]) => void;
  handleStreamMessage: (message: SseMessage) => void;
  setStatus: (status: StreamStatus) => void;
  toggleCategory: (category: Category) => void;
  setCountry: (iso: string | null) => void;
  select: (id: string | null) => void;
  reset: () => void;
}

export const initialEventsState = {
  byId: {} as Record<string, LiveEvent>,
  list: [] as LiveEvent[],
  hidden: [] as Category[],
  country: null as string | null,
  stats: null as StoreStats | null,
  status: 'offline' as StreamStatus,
  loaded: false,
  error: null as string | null,
  selectedId: null as string | null,
};

/** Newest first, with the id as a tie-break so the order is stable. */
function toList(byId: Record<string, LiveEvent>): LiveEvent[] {
  return Object.values(byId).sort(
    (a, b) => b.published_at.localeCompare(a.published_at) || a.id.localeCompare(b.id),
  );
}

/** Drops the oldest observed events once the client mirror exceeds its cap. */
function bounded(byId: Record<string, LiveEvent>): Record<string, LiveEvent> {
  const entries = Object.entries(byId);
  if (entries.length <= MAX_CLIENT_EVENTS) return byId;
  entries.sort(([, a], [, b]) => (a.observed_at < b.observed_at ? -1 : 1));
  return Object.fromEntries(entries.slice(entries.length - MAX_CLIENT_EVENTS));
}

function without(byId: Record<string, LiveEvent>, ids: readonly string[]): Record<string, LiveEvent> {
  const gone = new Set(ids);
  return Object.fromEntries(Object.entries(byId).filter(([id]) => !gone.has(id)));
}

export const useEventsStore = create<EventsState>()((set, get) => ({
  ...initialEventsState,

  load: async () => {
    try {
      const [events, stats] = await Promise.all([fetchEvents({ limit: 2000 }), fetchStats()]);
      const byId: Record<string, LiveEvent> = {};
      for (const event of events) byId[event.id] = event;
      set({ byId, list: toList(byId), stats, loaded: true, error: null });
    } catch (caught) {
      set({ error: describeError(caught), loaded: true });
    }
  },

  applyUpsert: (events) => {
    if (events.length === 0) return;
    const byId = { ...bounded(get().byId) };
    for (const event of events) byId[event.id] = event;
    set({ byId, list: toList(byId) });
  },

  applyExpire: (ids) => {
    if (ids.length === 0) return;
    const byId = without(get().byId, ids);
    const selectedId = get().selectedId;
    set({
      byId,
      list: toList(byId),
      selectedId: selectedId !== null && !(selectedId in byId) ? null : selectedId,
    });
  },

  handleStreamMessage: (message) => {
    let payload: unknown = null;
    try {
      payload = JSON.parse(message.data) as unknown;
    } catch {
      return;
    }
    if (message.event === 'event.upsert') {
      const parsed = streamUpsertSchema.safeParse(payload);
      if (parsed.success) get().applyUpsert(parsed.data.events);
    } else if (message.event === 'event.expire') {
      const parsed = streamExpireSchema.safeParse(payload);
      if (parsed.success) get().applyExpire(parsed.data.ids);
    }
  },

  setStatus: (status) => {
    set({ status });
  },

  toggleCategory: (category) => {
    const hidden = get().hidden;
    set({
      hidden: hidden.includes(category)
        ? hidden.filter((item) => item !== category)
        : [...hidden, category],
    });
  },

  setCountry: (iso) => {
    set({ country: iso });
  },

  select: (id) => {
    set({ selectedId: id });
  },

  reset: () => {
    set({ ...initialEventsState });
  },
}));

/** Events inside the nation filter, before category switches apply. */
export function filterByCountry(events: LiveEvent[], country: string | null): LiveEvent[] {
  return country === null ? events : events.filter((event) => event.country_iso === country);
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
