/**
 * The browser's mirror of the live store: a bounded map of events kept current by
 * the stream, plus which categories are shown and which event is selected.
 */
import { create } from 'zustand';
import { boundedEvents, mergeSnapshots } from './events.coverage';

import { loadCoverageSupplements } from './events.supplements';

import { fetchEvents, fetchStats } from '@/lib/api/events';
import { streamExpireSchema, streamResyncSchema, streamUpsertSchema } from '@/lib/api/eventSchemas';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import type { SseMessage, StreamStatus } from '@/lib/sse';

export const MAX_CLIENT_EVENTS = 5_000;
export const SNAPSHOT_LIMIT = 2_000;

export interface EventsState {
  byId: Record<string, LiveEvent>;
  list: LiveEvent[];
  hidden: Category[];
  /** ISO 3166-1 alpha-2 code of the nation filter, or null for the whole world. */
  country: string | null;
  /** Show only events published within this many hours, or null for the whole window. */
  windowHours: number | null;
  stats: StoreStats | null;
  status: StreamStatus;
  loaded: boolean;
  loading: boolean;
  snapshotCount: number | null;
  snapshotLimited: boolean;
  mirrorCapped: boolean;
  error: string | null;
  selectedId: string | null;
  load: () => Promise<void>;
  cancelLoad: () => void;
  applyUpsert: (events: LiveEvent[]) => void;
  applyExpire: (ids: string[]) => void;
  handleStreamMessage: (message: SseMessage) => void;
  setStatus: (status: StreamStatus) => void;
  toggleCategory: (category: Category) => void;
  setCountry: (iso: string | null) => void;
  setWindow: (hours: number | null) => void;
  select: (id: string | null) => void;
  reset: () => void;
}

export const initialEventsState = {
  byId: {} as Record<string, LiveEvent>,
  list: [] as LiveEvent[],
  hidden: [] as Category[],
  country: null as string | null,
  windowHours: null as number | null,
  stats: null as StoreStats | null,
  status: 'offline' as StreamStatus,
  loaded: false,
  loading: false,
  snapshotCount: null as number | null,
  snapshotLimited: false,
  mirrorCapped: false,
  error: null as string | null,
  selectedId: null as string | null,
};

/** Newest first, with the id as a tie-break so the order is stable. */
function toList(byId: Record<string, LiveEvent>): LiveEvent[] {
  return Object.values(byId).sort(
    (a, b) =>
      (b.published_at ?? '').localeCompare(a.published_at ?? '') || a.id.localeCompare(b.id),
  );
}

function without(
  byId: Record<string, LiveEvent>,
  ids: readonly string[],
): Record<string, LiveEvent> {
  const gone = new Set(ids);
  return Object.fromEntries(Object.entries(byId).filter(([id]) => !gone.has(id)));
}

export const useEventsStore = create<EventsState>()((set, get) => {
  let resyncRequested = false;
  const needsResync = () => resyncRequested;
  let pending: {
    controller: AbortController;
    changes: Map<string, LiveEvent | null>;
    overflow: boolean;
  } | null = null;
  const record = (id: string, event: LiveEvent | null) => {
    if (!pending || pending.overflow) return;
    if (!pending.changes.has(id) && pending.changes.size >= MAX_CLIENT_EVENTS) {
      // Never drop tombstones or overwrite fresh events with an unsafe snapshot.
      pending.overflow = true;
      pending.changes.clear();
      return;
    }
    pending.changes.set(id, event);
  };
  return {
    ...initialEventsState,

    load: async () => {
      resyncRequested = false;
      pending?.controller.abort();
      const request = {
        controller: new AbortController(),
        changes: new Map<string, LiveEvent | null>(),
        overflow: false,
      };
      pending = request;
      const isCurrent = () => pending === request && !request.controller.signal.aborted;
      set({ loading: true, error: null });
      try {
        const [events, stats] = await Promise.all([
          fetchEvents({ limit: SNAPSHOT_LIMIT }, request.controller.signal),
          fetchStats(request.controller.signal),
        ]);
        if (!isCurrent()) return;
        const supplement = await loadCoverageSupplements(events, stats, request.controller.signal);
        if (!isCurrent()) return;
        if (needsResync()) return;
        if (request.overflow) {
          set({
            error:
              'Live updates exceeded the snapshot reconciliation limit. Displaying received updates; reload to resynchronise.',
            loaded: true,
          });
          return;
        }
        const merged = mergeSnapshots(events, supplement.events);
        const snapshotCount = merged.size;
        for (const [id, event] of request.changes) {
          if (event === null) merged.delete(id);
          else merged.set(id, event);
        }
        const byId = Object.fromEntries(merged);
        const capped = boundedEvents(byId, MAX_CLIENT_EVENTS, get().selectedId);
        const selectedId = get().selectedId;
        set({
          byId: capped,
          list: toList(capped),
          stats,
          loaded: true,
          error: supplement.error,
          snapshotCount,
          snapshotLimited:
            events.length >= SNAPSHOT_LIMIT || supplement.limited || stats.total > snapshotCount,
          mirrorCapped: Object.keys(byId).length > MAX_CLIENT_EVENTS,
          selectedId: selectedId !== null && !(selectedId in capped) ? null : selectedId,
        });
      } catch (caught) {
        if (pending === request && !request.controller.signal.aborted) {
          set({ error: describeError(caught), loaded: true });
        }
      } finally {
        // Cancel a sibling request if Promise.all failed before it completed.
        request.controller.abort();
        if (pending === request) {
          pending = null;
          set({ loading: false });
          if (needsResync()) void get().load();
        }
      }
    },

    cancelLoad: () => {
      resyncRequested = false;
      pending?.controller.abort();
      pending = null;
      set({ loading: false });
    },

    applyUpsert: (events) => {
      if (events.length === 0) return;
      const merged = { ...get().byId };
      for (const event of events) {
        merged[event.id] = event;
        record(event.id, event);
      }
      const byId = boundedEvents(merged, MAX_CLIENT_EVENTS, get().selectedId);
      const selectedId = get().selectedId;
      set({
        byId,
        list: toList(byId),
        mirrorCapped: get().mirrorCapped || Object.keys(merged).length > MAX_CLIENT_EVENTS,
        selectedId: selectedId !== null && !(selectedId in byId) ? null : selectedId,
      });
    },

    applyExpire: (ids) => {
      if (ids.length === 0) return;
      for (const id of ids) record(id, null);
      if (!ids.some((id) => id in get().byId)) return;
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
      } else if (message.event === 'event.resync') {
        const parsed = streamResyncSchema.safeParse(payload);
        if (!parsed.success) return;
        if (parsed.data.reason !== 'snapshot_required')
          set({
            byId: {},
            list: [],
            selectedId: null,
            stats: null,
            loaded: false,
            snapshotCount: null,
            snapshotLimited: false,
            mirrorCapped: false,
          });
        if (pending) {
          // Several bulk feeds can finish together. Finish this bounded snapshot,
          // then reconcile once more instead of repeatedly aborting useful work.
          resyncRequested = true;
          return;
        }
        get().cancelLoad();
        void get().load();
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
    setWindow: (hours) => {
      set({ windowHours: hours });
    },

    select: (id) => {
      set({ selectedId: id });
    },

    reset: () => {
      resyncRequested = false;
      pending?.controller.abort();
      pending = null;
      set({ ...initialEventsState });
    },
  };
});

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
