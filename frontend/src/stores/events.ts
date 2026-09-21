/**
 * The browser's mirror of the live store: a bounded map of events kept current by
 * the stream, plus which categories are shown and which event is selected.
 */
import { create } from 'zustand';
import { boundedEvents, mergeSnapshots } from './events.coverage';
import { SnapshotRefresh } from './events.refresh';
import { publishEventChange } from './events.changes';
import { selectionAfterMirrorUpdate, type SelectionOwner } from './events.selection';
export {
  filterByCountry,
  filterByWindow,
  selectCountryEvents,
  selectVisibleEvents,
  selectSelectedEvent,
  countByCategory,
} from './events.selectors';

import { insideCoverage, type CoverageBounds } from './events.geography';
import { loadCoverageSupplements } from './events.supplements';

import { fetchEvents, fetchStats } from '@/lib/api/events';
import { streamExpireSchema, streamResyncSchema, streamUpsertSchema } from '@/lib/api/eventSchemas';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { ORDERED_CATEGORIES } from '@/lib/categories';
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
  coverageBounds: CoverageBounds | null;
  setCoverageBounds: (bounds: CoverageBounds | null) => void;
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
  selectionOwner: SelectionOwner;
  /** Flush queued deltas before opening a new snapshot reconciliation journal. */
  onSnapshotStart: (flush: () => void) => () => void;
  load: () => Promise<void>;
  cancelLoad: () => void;
  applyUpsert: (events: LiveEvent[]) => void;
  applyExpire: (ids: string[]) => void;
  handleStreamMessage: (message: SseMessage) => void;
  setStatus: (status: StreamStatus) => void;
  toggleCategory: (category: Category) => void;
  setCountry: (iso: string | null) => void;
  setWindow: (hours: number | null) => void;
  select: (id: string | null, owner?: SelectionOwner) => void;
  reset: () => void;
}

export const initialEventsState = {
  byId: {} as Record<string, LiveEvent>,
  list: [] as LiveEvent[],
  hidden: ORDERED_CATEGORIES.filter((category) => category !== 'conflict'),
  country: null as string | null,
  coverageBounds: null as CoverageBounds | null,
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
  selectionOwner: 'mirror' as SelectionOwner,
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
  const snapshotBarriers = new Set<() => void>();
  const refresh = new SnapshotRefresh(() => {
    void get().load();
  });
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

    onSnapshotStart: (flush) => {
      snapshotBarriers.add(flush);
      return () => {
        snapshotBarriers.delete(flush);
      };
    },

    load: async () => {
      for (const flush of snapshotBarriers) flush();
      refresh.started();
      pending?.controller.abort();
      const request = {
        controller: new AbortController(),
        changes: new Map<string, LiveEvent | null>(),
        overflow: false,
      };
      pending = request;
      const isCurrent = () => pending === request && !request.controller.signal.aborted;
      const bounds = get().coverageBounds;
      const scope = { sampling: 'geographic' as const, ...(bounds ? { bbox: bounds } : {}) };
      set({ loading: true, error: null });
      try {
        const [events, stats] = await Promise.all([
          fetchEvents({ limit: SNAPSHOT_LIMIT, ...scope }, request.controller.signal),
          fetchStats(request.controller.signal),
        ]);
        if (!isCurrent()) return;
        const supplement = await loadCoverageSupplements(
          events,
          stats,
          request.controller.signal,
          scope,
        );
        if (!isCurrent()) return;
        if (request.overflow) {
          set({
            error:
              'Live updates exceeded the snapshot reconciliation limit. Displaying received updates; reload to resynchronise.',
            loaded: true,
          });
          return;
        }
        const merged = mergeSnapshots(events, supplement.events);
        for (const [id, event] of merged) if (!insideCoverage(event, bounds)) merged.delete(id);
        const snapshotCount = merged.size;
        for (const [id, event] of request.changes) {
          if (event === null) merged.delete(id);
          else merged.set(id, event);
        }
        const byId = Object.fromEntries(merged);
        const capped = boundedEvents(byId, MAX_CLIENT_EVENTS, get().selectedId);
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
          selectedId: selectionAfterMirrorUpdate(get(), capped),
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
          refresh.finished();
        }
      }
    },

    cancelLoad: () => {
      refresh.cancel();
      pending?.controller.abort();
      pending = null;
      set({ loading: false });
    },

    setCoverageBounds: (coverageBounds) => {
      get().cancelLoad();
      set({ coverageBounds });
    },

    applyUpsert: (events) => {
      if (events.length === 0) return;
      publishEventChange({ kind: 'upsert', events });
      const current = get();
      let merged = current.byId;
      for (const event of events) {
        const visible = insideCoverage(event, current.coverageBounds);
        record(event.id, visible ? event : null);
        if (visible ? merged[event.id] === event : !(event.id in merged)) continue;
        if (merged === current.byId) merged = { ...current.byId };
        if (visible) merged[event.id] = event;
        else Reflect.deleteProperty(merged, event.id);
      }
      if (merged === current.byId) return;
      const byId = boundedEvents(merged, MAX_CLIENT_EVENTS, current.selectedId);
      set({
        byId,
        list: toList(byId),
        mirrorCapped: get().mirrorCapped || Object.keys(merged).length > MAX_CLIENT_EVENTS,
        selectedId: selectionAfterMirrorUpdate(get(), byId),
      });
    },

    applyExpire: (ids) => {
      if (ids.length === 0) return;
      publishEventChange({ kind: 'expire', ids });
      for (const id of ids) record(id, null);
      const selected = get().selectedId;
      if (selected !== null && ids.includes(selected)) get().select(null);
      if (!ids.some((id) => id in get().byId)) return;
      const byId = without(get().byId, ids);
      set({
        byId,
        list: toList(byId),
        selectedId: selectionAfterMirrorUpdate(get(), byId),
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
        if (parsed.data.reason === 'snapshot_required') {
          // A bulk update is a refresh hint, not evidence that this snapshot is unsafe.
          // Publish useful completed work and coalesce one bounded follow-up.
          refresh.request(pending !== null);
          return;
        }
        publishEventChange({ kind: 'reset' });
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
        // A real stream gap invalidates the in-flight snapshot and its delta journal.
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

    select: (id, owner = 'mirror') => {
      set({ selectedId: id, selectionOwner: id === null ? 'mirror' : owner });
    },

    reset: () => {
      publishEventChange({ kind: 'reset' });
      refresh.cancel();
      pending?.controller.abort();
      pending = null;
      set({ ...initialEventsState });
    },
  };
});
