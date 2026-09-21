import type { LiveEvent } from '@/lib/api/eventSchemas';

/** Observation time is the version signal; publication time breaks observation ties. */
export function compareEventFreshness(a: LiveEvent, b: LiveEvent): number {
  return (
    Date.parse(a.observed_at) - Date.parse(b.observed_at) ||
    Date.parse(a.published_at ?? a.observed_at) - Date.parse(b.published_at ?? b.observed_at)
  );
}

/** A bounded supplemental page, with removals journalled while its replacement loads. */
export class LiveEventSnapshot {
  private items: LiveEvent[] = [];
  private listeners = new Set<() => void>();
  private pending: {
    baseline: Map<string, LiveEvent>;
    changes: Map<string, LiveEvent | null>;
    overflow: boolean;
  } | null = null;

  constructor(
    private readonly matches: (event: LiveEvent) => boolean,
    private readonly limit = 300,
    private readonly journalLimit = 5000,
  ) {}

  getSnapshot = () => this.items;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private publish(items: LiveEvent[]) {
    this.items = items;
    for (const listener of this.listeners) listener();
  }

  begin(live: readonly LiveEvent[]) {
    // Baseline references do not consume the in-flight change allowance. A full
    // viewport mirror is normal, and can include a newer non-news correction.
    const baseline = new Map(this.items.map((event) => [event.id, event]));
    for (const event of live.slice(0, this.journalLimit)) {
      const previous = baseline.get(event.id);
      if (!previous || compareEventFreshness(event, previous) >= 0) baseline.set(event.id, event);
    }
    const pending = { baseline, changes: new Map<string, LiveEvent | null>(), overflow: false };
    this.pending = pending;
    return pending;
  }

  private record(id: string, event: LiveEvent | null) {
    const pending = this.pending;
    if (!pending || pending.overflow) return;
    const previous = pending.changes.get(id);
    if (previous && event && compareEventFreshness(event, previous) < 0) return;
    if (!pending.changes.has(id) && pending.changes.size >= this.journalLimit) {
      pending.overflow = true;
      pending.changes.clear();
    } else pending.changes.set(id, event);
  }

  upsert(events: readonly LiveEvent[]) {
    const replacements = new Map<string, LiveEvent>();
    for (const event of events) {
      this.record(event.id, event);
      replacements.set(event.id, event);
    }
    const items = this.items.flatMap((previous) => {
      const next = replacements.get(previous.id);
      if (!next || compareEventFreshness(next, previous) < 0) return [previous];
      return this.matches(next) ? [next] : [];
    });
    if (
      items.length !== this.items.length ||
      items.some((event, index) => event !== this.items[index])
    )
      this.publish(items);
  }

  expire(ids: readonly string[]) {
    for (const id of ids) this.record(id, null);
    const removed = new Set(ids);
    const items = this.items.filter((event) => !removed.has(event.id));
    if (items.length !== this.items.length) this.publish(items);
  }

  finish(pending: ReturnType<LiveEventSnapshot['begin']>, received: readonly LiveEvent[]) {
    if (this.pending !== pending) return;
    this.pending = null;
    if (pending.overflow) throw new Error('Snapshot reconciliation exceeded its bounded journal.');
    const items = received.slice(0, this.limit).flatMap((event) => {
      const change = pending.changes.get(event.id);
      if (change === null) return [];
      const baseline = pending.baseline.get(event.id);
      const previous = baseline && compareEventFreshness(baseline, event) >= 0 ? baseline : event;
      const current = change && compareEventFreshness(change, previous) >= 0 ? change : previous;
      return this.matches(current) ? [current] : [];
    });
    this.publish(items);
  }

  cancel(pending: ReturnType<LiveEventSnapshot['begin']>) {
    if (this.pending === pending) this.pending = null;
  }

  clear() {
    this.pending = null;
    this.publish([]);
  }
}
