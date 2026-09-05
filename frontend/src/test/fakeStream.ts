/** Stand-in for EventStreamClient: tests push frames and statuses by hand. */
import { vi } from 'vitest';

import type { SseMessage, StreamOptions, StreamStatus } from '@/lib/sse';

export class FakeEventStreamClient {
  static instances: FakeEventStreamClient[] = [];

  readonly start = vi.fn();
  readonly stop = vi.fn();

  constructor(readonly options: StreamOptions) {
    FakeEventStreamClient.instances.push(this);
  }

  emit(message: SseMessage): void {
    this.options.onMessage(message);
  }

  setStatus(status: StreamStatus): void {
    this.options.onStatus(status);
  }

  static reset(): void {
    FakeEventStreamClient.instances = [];
  }
}

export { FakeEventStreamClient as EventStreamClient };
