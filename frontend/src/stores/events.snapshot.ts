/**
 * Snapshot requests for the browser mirror. A full load replaces the mirror; after a bulk
 * feed update, a partition refresh replaces only the categories that update touched and
 * keeps every other record as it is. Stream deltas that arrive during either request are
 * journalled and win over the response, so a refresh never restores older data. A first
 * load publishes its primary page early; a refresh of a complete mirror publishes once.
 */
import { fetchEvents, fetchStats, type EventsQuery } from '@/lib/api/events';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import type { EventsState } from './events';
import { toList } from './events.batch';
import { boundedEvents, mergeSnapshotRecords, mergeSnapshots } from './events.coverage';
import { insideCoverage, type CoverageBounds } from './events.geography';
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
  retainedSelection: boolean;
}

interface Snapshot {
  events: LiveEvent[];
  stats: StoreStats;
  merged: Map<string, LiveEvent>;
  bounds: CoverageBounds | null;
  area: Pick<EventsQuery, 'bbox' | 'sampling'>;
  partial: boolean;
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
    const request = {
      controller: new AbortController(),
      changes: new Map(),
      overflow: false,
      retainedSelection: false,
    };
    pending = request;
    return request;
  }

  /** Fetch the primary snapshot before slower category supplements start. */
  async function fetchPrimary(
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
    if (request.overflow) {
      set({ error: OVERFLOW_ERROR, loaded: true });
      return null;
    }
    const merged = mergeSnapshots(events, []);
    for (const [id, event] of merged) {
      if (!insideCoverage(event, bounds) || (scope !== null && !scope.has(event.category)))
        merged.delete(id);
    }
    return {
      events,
      stats,
      merged,
      bounds,
      area,
      partial: scope !== null,
      error: null,
      limited: false,
    };
  }

  /** Journalled deltas are newer than any response, then the browser bound applies. */
  function publish(
    request: Request,
    snapshot: Snapshot,
    records: Map<string, LiveEvent>,
    final = false,
  ) {
    const current = get();
    for (const [id, event] of request.changes) {
      if (event === null) records.delete(id);
      else records.set(id, event);
    }
    const selectedId = current.selectedId;
    const previousSelection = selectedId === null ? undefined : current.byId[selectedId];
    if (
      !final &&
      selectedId !== null &&
      !records.has(selectedId) &&
      previousSelection &&
      insideCoverage(previousSelection, snapshot.bounds)
    ) {
      // Keep the selected marker and details while its category is still loading.
      // It is not counted as part of the new snapshot and is rechecked at the end.
      records.set(selectedId, previousSelection);
      request.retainedSelection = true;
    }
    const byId = Object.fromEntries(records);
    const capped = boundedEvents(byId, MAX_CLIENT_EVENTS, selectedId);
    const snapshotCount = [...counts.values()].reduce((sum, count) => sum + count, 0);
    failures = 0;
    return {
      byId: capped,
      stats: snapshot.stats,
      loaded: true,
      snapshotCount,
      // A partition cannot prove that untouched categories from the last full load are complete.
      snapshotLimited:
        (snapshot.partial && current.snapshotLimited) ||
        snapshot.events.length >= SNAPSHOT_LIMIT ||
        snapshot.limited ||
        (snapshot.bounds === null && snapshot.stats.total > snapshotCount),
      mirrorCapped: Object.keys(byId).length > MAX_CLIENT_EVENTS,
      // A selected record can be in a pending supplement. Resolve a missing selection
      // only after the final request, while a live expiry still clears it immediately.
      selectedId: current.selectedId,
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
    apply: (request: Request, snapshot: Snapshot, final?: boolean) => void,
  ) {
    const request = begin();
    // A refresh over a complete mirror publishes once, at the end. Publishing the primary
    // page first would drop supplement-only records until their request lands again.
    const atomic = soft && complete;
    set(scope === null ? { loading: true, error: null } : { loading: true });
    try {
      const snapshot = await fetchPrimary(request, scope);
      if (snapshot === null) return;
      if (!atomic) apply(request, snapshot);
      if (!isCurrent(request)) return;
      // A short bbox result is the whole scoped query. Global statistics cannot
      // justify another read for this viewport; a full page may still hide sources.
      if (snapshot.bounds === null || snapshot.events.length >= SNAPSHOT_LIMIT)
        await loadCoverageSupplements(
          snapshot.events,
          snapshot.stats,
          request.controller.signal,
          snapshot.area,
          scope,
          (progress) => {
            if (!isCurrent(request) || request.overflow) return;
            snapshot.error = progress.error;
            const limitChanged = snapshot.limited !== progress.limited;
            snapshot.limited = progress.limited;
            if (progress.events.length > 0) {
              mergeSnapshotRecords(
                snapshot.merged,
                progress.events.filter(
                  (event) =>
                    insideCoverage(event, snapshot.bounds) &&
                    (scope === null || scope.has(event.category)),
                ),
              );
            }
            if (atomic) return;
            if (progress.events.length > 0 || limitChanged) apply(request, snapshot);
            else {
              const current = get();
              const error =
                progress.error ??
                (scope !== null && current.error !== REFRESH_FAILED_ERROR ? current.error : null);
              if (current.error !== error) set({ error });
            }
          },
        );
      if (!isCurrent(request)) return;
      if (request.overflow) {
        set({ error: OVERFLOW_ERROR, loaded: true });
        return;
      }
      if (atomic || request.retainedSelection) apply(request, snapshot, true);
      if (!isCurrent(request)) return;
      if (scope === null) complete = true;
      const current = get();
      const selectedId = selectionAfterMirrorUpdate(current, current.byId);
      if (selectedId !== current.selectedId) set({ selectedId });
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
    return run(null, soft, (request, snapshot, final) => {
      countPartitions(snapshot.merged, null);
      const update = publish(request, snapshot, new Map(snapshot.merged), final);
      set({ ...update, list: toList(update.byId), error: snapshot.error });
    });
  }

  function loadPartition(scope: ReadonlySet<Category>) {
    return run(scope, true, (request, snapshot, final) => {
      const current = get();
      const records = new Map<string, LiveEvent>();
      for (const [id, event] of Object.entries(current.byId))
        if (!scope.has(event.category)) records.set(id, event);
      // Replace the whole partition: records no longer in it, or expired, are removed.
      for (const [id, event] of snapshot.merged) records.set(id, event);
      countPartitions(snapshot.merged, scope);
      const update = publish(request, snapshot, records, final);
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
