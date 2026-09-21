import type { LiveEvent } from '@/lib/api/eventSchemas';

export type EventChange =
  | { kind: 'upsert'; events: readonly LiveEvent[] }
  | { kind: 'expire'; ids: readonly string[] }
  | { kind: 'reset' };

const listeners = new Set<(change: EventChange) => void>();

/** Raw stream changes reach supplemental snapshots even outside the viewport mirror. */
export function subscribeEventChanges(listener: (change: EventChange) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function publishEventChange(change: EventChange) {
  for (const listener of listeners) listener(change);
}
