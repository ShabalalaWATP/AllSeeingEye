import type { LiveEvent } from '@/lib/api/eventSchemas';

import { insideCoverage, type CoverageBounds } from './events.geography';

export function compareText(a: string, b: string): number {
  return a.localeCompare(b);
}

/** Newest first, with the id as a tie-break so the order is stable. */
export function newestFirst(a: LiveEvent, b: LiveEvent): number {
  return compareText(b.published_at ?? '', a.published_at ?? '') || compareText(a.id, b.id);
}

/**
 * The mirror as a list, newest first. Records unchanged since `previous` keep their sorted
 * order, so a stream batch sorts only its own records and merges them in: the same order
 * as a full sort, without re-sorting 5,000 retained records every quarter second.
 */
export function toList(
  byId: Record<string, LiveEvent>,
  previous: readonly LiveEvent[] = [],
): LiveEvent[] {
  const kept = previous.filter((event) => byId[event.id] === event);
  const sorted = kept.every((event, index) => {
    const before = kept[index - 1];
    return before === undefined || newestFirst(before, event) < 0;
  });
  if (kept.length === 0 || !sorted) return Object.values(byId).sort(newestFirst);
  const retained = new Set(kept);
  const added = Object.values(byId)
    .filter((event) => !retained.has(event))
    .sort(newestFirst);
  const list: LiveEvent[] = [];
  let right = 0;
  for (const event of kept) {
    for (let next = added[right]; next !== undefined && newestFirst(event, next) > 0;) {
      list.push(next);
      next = added[++right];
    }
    list.push(event);
  }
  list.push(...added.slice(right));
  return list;
}

/**
 * Applies a batch's expiries, then its upserts, to the mirror in one pass. Every change is
 * journalled through `record`, including records outside the coverage bounds. Returns null
 * when the mirror's visible contents did not change, so callers can skip a rebuild.
 */
export function mergeMirrorBatch(
  byId: Record<string, LiveEvent>,
  bounds: CoverageBounds | null,
  expired: readonly string[],
  events: readonly LiveEvent[],
  record: (id: string, event: LiveEvent | null) => void,
): Record<string, LiveEvent> | null {
  let merged = byId;
  const writable = () => {
    if (merged === byId) merged = { ...byId };
    return merged;
  };
  for (const id of expired) {
    record(id, null);
    if (id in merged) Reflect.deleteProperty(writable(), id);
  }
  for (const event of events) {
    const visible = insideCoverage(event, bounds);
    record(event.id, visible ? event : null);
    if (visible ? merged[event.id] === event : !(event.id in merged)) continue;
    if (visible) writable()[event.id] = event;
    else Reflect.deleteProperty(writable(), event.id);
  }
  return merged === byId ? null : merged;
}
