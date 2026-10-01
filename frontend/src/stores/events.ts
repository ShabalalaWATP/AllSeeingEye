/**
 * The browser's mirror of the live store: a bounded map of events kept current by
 * the stream, plus which categories are shown and which event is selected.
 */
import { create } from 'zustand';
import { boundedEvents } from './events.coverage';
import { publishEventChange } from './events.changes';
import { selectionAfterMirrorUpdate, type SelectionOwner } from './events.selection';
import { mergeMirrorBatch, toList } from './events.batch';
import { MAX_CLIENT_EVENTS } from './events.limits';
import { createSnapshotLoader } from './events.snapshot';
export { MAX_CLIENT_EVENTS, SNAPSHOT_LIMIT } from './events.limits';
export {
  filterByCountry,
  filterByWindow,
  selectCountryEvents,
  selectVisibleEvents,
  selectSelectedEvent,
  countByCategory,
} from './events.selectors';

import type { CoverageBounds } from './events.geography';

import {
  refreshPartitions,
  streamExpireSchema,
  streamResyncSchema,
  streamUpsertSchema,
} from '@/lib/api/eventSchemas';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { ORDERED_CATEGORIES } from '@/lib/categories';
import type { SseMessage, StreamStatus } from '@/lib/sse';

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
  /** Expiries then upserts, as one bounded mirror update and one store notification. */
  applyBatch: (expired: readonly string[], events: readonly LiveEvent[]) => void;
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

export const useEventsStore = create<EventsState>()((set, get) => {
  const snapshots = createSnapshotLoader(get, set);
  return {
    ...initialEventsState,

    onSnapshotStart: snapshots.onSnapshotStart,

    load: snapshots.load,

    cancelLoad: () => {
      snapshots.cancel();
    },

    setCoverageBounds: (coverageBounds) => {
      get().cancelLoad();
      set({ coverageBounds });
    },

    applyUpsert: (events) => {
      get().applyBatch([], events);
    },

    applyExpire: (ids) => {
      get().applyBatch(ids, []);
    },

    applyBatch: (expired, events) => {
      if (expired.length > 0) publishEventChange({ kind: 'expire', ids: expired });
      if (events.length > 0) publishEventChange({ kind: 'upsert', events });
      const current = get();
      const merged = mergeMirrorBatch(
        current.byId,
        current.coverageBounds,
        expired,
        events,
        snapshots.record,
      );
      // An expired selection clears whoever owns it, as the stream says the record is gone.
      const selection =
        current.selectedId !== null && expired.includes(current.selectedId)
          ? { selectedId: null, selectionOwner: 'mirror' as const }
          : current;
      if (merged === null) {
        if (selection !== current) set(selection);
        return;
      }
      const byId = boundedEvents(merged, MAX_CLIENT_EVENTS, selection.selectedId);
      set({
        byId,
        list: toList(byId, current.list),
        mirrorCapped: current.mirrorCapped || Object.keys(merged).length > MAX_CLIENT_EVENTS,
        selectedId: selectionAfterMirrorUpdate(selection, byId),
        selectionOwner: selection.selectionOwner,
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
          // Publish useful completed work and coalesce one bounded follow-up of the
          // partitions it names, or of everything when it names none it recognises.
          snapshots.requestRefresh(refreshPartitions(parsed.data.categories));
          return;
        }
        publishEventChange({ kind: 'reset' });
        snapshots.invalidate();
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
      snapshots.cancel();
      snapshots.invalidate();
      set({ ...initialEventsState });
    },
  };
});
