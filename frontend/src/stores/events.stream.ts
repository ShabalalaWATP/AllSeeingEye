import type { LiveEvent } from '@/lib/api/eventSchemas';
import { streamExpireSchema, streamResyncSchema, streamUpsertSchema } from '@/lib/api/eventSchemas';
import type { SseMessage } from '@/lib/sse';

export const STREAM_BATCH_MS = 250;
export const MAX_PENDING_EVENTS = 5_000;

interface Sink {
  applyUpsert: (events: LiveEvent[]) => void;
  applyExpire: (ids: string[]) => void;
  handleStreamMessage: (message: SseMessage) => void;
}

/** Coalesce sensor bursts before publishing a new 5,000-record React/GPU snapshot. */
export class EventUpdateBatch {
  private changes = new Map<string, LiveEvent | null>();
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly sink: () => Sink) {}

  receive(message: SseMessage): void {
    if (!['event.upsert', 'event.expire'].includes(message.event)) {
      // Keep queued deltas before a soft refresh. Authority changes never wait for sensors.
      if (message.event === 'event.resync') {
        let soft = false;
        try {
          const parsed = streamResyncSchema.safeParse(JSON.parse(message.data) as unknown);
          if (!parsed.success) return;
          soft = parsed.data.reason === 'snapshot_required';
        } catch {
          return;
        }
        if (soft) this.flush();
        else this.clear();
      } else if (message.event === 'access.changed') this.clear();
      this.sink().handleStreamMessage(message);
      return;
    }
    let payload: unknown;
    try {
      payload = JSON.parse(message.data) as unknown;
    } catch {
      return;
    }
    if (message.event === 'event.upsert') {
      const parsed = streamUpsertSchema.safeParse(payload);
      if (!parsed.success) return;
      for (const event of parsed.data.events) this.record(event.id, event);
    } else {
      const parsed = streamExpireSchema.safeParse(payload);
      if (!parsed.success) return;
      for (const id of parsed.data.ids) this.record(id, null);
    }
  }

  private record(id: string, event: LiveEvent | null): void {
    // Bound memory without losing tombstones or the established source reservations.
    if (!this.changes.has(id) && this.changes.size === MAX_PENDING_EVENTS) this.flush();
    this.changes.set(id, event);
    this.timer ??= setTimeout(() => this.flush(), STREAM_BATCH_MS);
  }

  flush(): void {
    if (!this.changes.size) return;
    const events: LiveEvent[] = [];
    const expired: string[] = [];
    for (const [id, event] of this.changes) {
      if (event === null) expired.push(id);
      else events.push(event);
    }
    this.clear();
    const sink = this.sink();
    sink.applyExpire(expired);
    sink.applyUpsert(events);
  }

  clear(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.changes.clear();
  }
}
