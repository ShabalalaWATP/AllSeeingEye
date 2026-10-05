import type { LiveEvent } from '@/lib/api/eventSchemas';
import { compareText } from './events.batch';

interface TimedEvent {
  event: LiveEvent;
  times: readonly [number, number];
}

function compare(a: TimedEvent, b: TimedEvent): number {
  return b.times[0] - a.times[0] || b.times[1] - a.times[1] || compareText(a.event.id, b.event.id);
}

function strictlyOrdered(events: readonly TimedEvent[]): boolean {
  return events.every((event, index) => {
    const before = events[index - 1];
    return before === undefined || compare(before, event) < 0;
  });
}

/**
 * A publication-ordered list is only a hint for eviction's different comparator.
 * Resolve current records and validate every sort input before reusing its order.
 * Null requests the original stable full sort over the untouched `keyed` sequence.
 * Nothing persists between calls, including category or priority decisions.
 */
export function mergeFreshnessHint<T extends TimedEvent>(
  byId: Record<string, LiveEvent>,
  keyed: readonly T[],
  previous: readonly LiveEvent[],
): T[] | null {
  if (previous.length === 0) return null;
  const keys = Object.keys(byId);
  if (keys.length !== keyed.length) return null;
  const current = new Map<string, T>();
  for (const [index, item] of keyed.entries()) {
    const { id } = item.event;
    if (
      typeof id !== 'string' ||
      keys[index] !== id ||
      !Object.hasOwn(byId, id) ||
      byId[id] !== item.event ||
      current.has(id) ||
      !Number.isFinite(item.times[0]) ||
      !Number.isFinite(item.times[1])
    )
      return null;
    current.set(id, item);
  }
  const previousIds = new Set<string>();
  const retained: T[] = [];
  for (const previousEvent of previous) {
    const { id } = previousEvent;
    if (typeof id !== 'string' || previousIds.has(id)) return null;
    previousIds.add(id);
    // Ordinary expiry is not a reason to reject an otherwise useful hint.
    const item = current.get(id);
    if (item !== undefined) retained.push(item);
  }
  if (retained.length === 0 || !strictlyOrdered(retained)) return null;
  const added = keyed.filter((item) => !previousIds.has(item.event.id));
  added.sort(compare);
  if (!strictlyOrdered(added)) return null;
  const result: T[] = [];
  let left = 0;
  let right = 0;
  while (left < retained.length && right < added.length) {
    const existing = retained[left];
    const incoming = added[right];
    if (existing === undefined || incoming === undefined) return null;
    const order = compare(existing, incoming);
    // Distinct IDs can collate equally. Only the original dictionary sequence
    // preserves stable-sort precedence across both streams in that case.
    if (order === 0) return null;
    if (order < 0) {
      result.push(existing);
      left++;
    } else {
      result.push(incoming);
      right++;
    }
  }
  result.push(...retained.slice(left), ...added.slice(right));
  return result;
}
