/**
 * Snapshot requests for the browser mirror. A full load replaces the mirror; after a bulk
 * feed update, a partition refresh replaces only the categories that update touched and
 * keeps every other record as it is. Stream deltas that arrive during either request are
 * journalled and win over the response, so a refresh never restores older data.
 */
import { fetchEvents, fetchStats, type EventsQuery } from '@/lib/api/events';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import type { EventsState } from './events';
import { toList } from './events.batch';
import { boundedEvents, mergeSnapshots } from './events.coverage';
import { insideCoverage } from './events.geography';
import { MAX_CLIENT_EVENTS, SNAPSHOT_LIMIT } from './events.limits';
import { MAX_REFRESH_RETRIES, SnapshotRefresh } from './events.refresh';
import { selectionAfterMirrorUpdate } from './events.selection';
import { loadCoverageSupplements } from './events.supplements';

export const OVERFLOW_ERROR =
  'Live updates exceeded the snapshot reconciliation limit. Displaying received updates; reload to resynchronise.';
export const REFRESH_FAILED_ERROR =
  'Live map refresh failed. Displaying the last loaded events; reload to try again.';

interface Request {
  controller: AbortController;
  changes: Map<string, LiveEvent | null>;
  overflow: boolean;
}

interface Snapshot {
  events: LiveEvent[];
  stats: StoreStats;
  merged: Map<string, LiveEvent>;
  error: string | null;
  limited: boolean;
}

type Get = () => EventsState;
type Set = (partial: Partial<EventsState>) => void;

export function createSnapshotLoader(get: Get, set: Set) {
  const barriers = new Set<() => void>();
  let pending: Request | null = null;
  // Records per partition in the latest snapshots, so the coverage summary stays honest.
  let counts = new Map<Category, number>();
  // Only a mirror that completed a full snapshot can refresh one partition at a time.
  let complete = false;
  let failures = 0;
  const refresh = new SnapshotRefresh((scope) => {
    void (scope === 'all' || !complete ? loadAll(true) : loadPartition(scope));
  });

  const isCurrent = (request: Request) => pending === request && !request.controller.signal.aborted;

  function begin(): Request {
    for (const flush of barriers) flush();
    refresh.started();
    pending?.controller.abort();
    const request = { controller: new AbortController(), changes: new Map(), overflow: false };
    pending = request;
    return request;
  }

  /** Fetch a bounded snapshot of the scope, or null when superseded or cancelled. */
  async function fetchSnapshot(
    request: Request,
    scope: ReadonlySet<Category> | null,
  ): Promise<Snapshot | null> {
    const bounds = get().coverageBounds;
    const area = { sampling: 'geographic' as const, ...(bounds ? { bbox: bounds } : {}) };
    const query: EventsQuery = { limit: SNAPSHOT_LIMIT, ...area };
    if (scope !== null) query.categories = [...scope];
    const { signal } = request.controller;
    const [events, stats] = await Promise.all([fetchEvents(query, signal), fetchStats(signal)]);
    if (!isCurrent(request)) return null;
    const supplement = await loadCoverageSupplements(events, stats, signal, area, scope);
    if (!isCurrent(request)) return null;
    if (request.overflow) {
      set({ error: OVERFLOW_ERROR, loaded: true });
      return null;
    }
    const merged = mergeSnapshots(events, supplement.events);
    for (const [id, event] of merged) {
      if (!insideCoverage(event, bounds) || (scope !== null && !scope.has(event.category)))
        merged.delete(id);
    }
    return { events, stats, merged, error: supplement.error, limited: supplement.limited };
  }

  /** Journalled deltas are newer than any response, then the browser bound applies. */
  function publish(request: Request, snapshot: Snapshot, records: Map<string, LiveEvent>) {
    const current = get();
    for (const [id, event] of request.changes) {
      if (event === null) records.delete(id);
      else records.set(id, event);
    }
    const byId = Object.fromEntries(records);
    const capped = boundedEvents(byId, MAX_CLIENT_EVENTS, current.selectedId);
    const snapshotCount = [...counts.values()].reduce((sum, count) => sum + count, 0);
    failures = 0;
    return {
      byId: capped,
      stats: snapshot.stats,
      loaded: true,
      snapshotCount,
      snapshotLimited:
        snapshot.events.length >= SNAPSHOT_LIMIT ||
        snapshot.limited ||
        snapshot.stats.total > snapshotCount,
      mirrorCapped: Object.keys(byId).length > MAX_CLIENT_EVENTS,
      selectedId: selectionAfterMirrorUpdate(current, capped),
    };
  }

  function countPartitions(records: Map<string, LiveEvent>, scope: ReadonlySet<Category> | null) {
    if (scope === null) counts = new Map();
    else for (const category of scope) counts.delete(category);
    for (const event of records.values())
      counts.set(event.category, (counts.get(event.category) ?? 0) + 1);
  }

  async function run(
    scope: ReadonlySet<Category> | null,
    soft: boolean,
    apply: (request: Request, snapshot: Snapshot) => void,
  ) {
    const request = begin();
    set(scope === null ? { loading: true, error: null } : { loading: true });
    try {
      const snapshot = await fetchSnapshot(request, scope);
      if (snapshot !== null) apply(request, snapshot);
    } catch (caught) {
      if (!isCurrent(request)) return;
      if (!soft) {
        set({ error: describeError(caught), loaded: true });
        return;
      }
      // A failed hint keeps the last valid mirror and tries again, a bounded number of times.
      failures += 1;
      if (failures <= MAX_REFRESH_RETRIES) refresh.retry(scope ?? 'all', failures);
      else set({ error: REFRESH_FAILED_ERROR });
    } finally {
      // Cancel a sibling request if Promise.all failed before it completed.
      request.controller.abort();
      if (pending === request) {
        pending = null;
        set({ loading: false });
        refresh.finished();
      }
    }
  }

  function loadAll(soft: boolean) {
    return run(null, soft, (request, snapshot) => {
      countPartitions(snapshot.merged, null);
      const update = publish(request, snapshot, new Map(snapshot.merged));
      complete = true;
      set({ ...update, list: toList(update.byId), error: snapshot.error });
    });
  }

  function loadPartition(scope: ReadonlySet<Category>) {
    return run(scope, true, (request, snapshot) => {
      const current = get();
      const records = new Map<string, LiveEvent>();
      for (const [id, event] of Object.entries(current.byId))
        if (!scope.has(event.category)) records.set(id, event);
      // Replace the whole partition: records no longer in it, or expired, are removed.
      for (const [id, event] of snapshot.merged) records.set(id, event);
      countPartitions(snapshot.merged, scope);
      const update = publish(request, snapshot, records);
      const error =
        snapshot.error ?? (current.error === REFRESH_FAILED_ERROR ? null : current.error);
      // Unchanged records keep their identity and order, so unrelated layers stay as they are.
      set({ ...update, list: toList(update.byId, current.list), error });
    });
  }

  return {
    onSnapshotStart: (flush: () => void) => {
      barriers.add(flush);
      return () => {
        barriers.delete(flush);
      };
    },
    load: () => loadAll(false),
    /** A bulk update's hint: the named partitions, or everything when none are known. */
    requestRefresh: (categories: readonly Category[] | null) => {
      refresh.request(pending !== null, categories);
    },
    record: (id: string, event: LiveEvent | null) => {
      if (!pending || pending.overflow) return;
      if (!pending.changes.has(id) && pending.changes.size >= MAX_CLIENT_EVENTS) {
        // Never drop tombstones or overwrite fresh events with an unsafe snapshot.
        pending.overflow = true;
        pending.changes.clear();
        return;
      }
      pending.changes.set(id, event);
    },
    cancel: () => {
      refresh.cancel();
      pending?.controller.abort();
      pending = null;
      set({ loading: false });
    },
    /** The mirror was cleared, so the next refresh must be a full snapshot. */
    invalidate: () => {
      complete = false;
      counts = new Map();
      failures = 0;
    },
  };
}

export type SnapshotLoader = ReturnType<typeof createSnapshotLoader>;
