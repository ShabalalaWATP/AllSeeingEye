/** Stand-in for EventStreamClient: tests push frames and statuses by hand. */
import { vi } from 'vitest';

import type { SseMessage, StreamOptions, StreamStatus } from '@/lib/sse';

export class FakeEventStreamClient {
  static instances: FakeEventStreamClient[] = [];
  static autoConnect = true;

  readonly start = vi.fn(() => {
    if (FakeEventStreamClient.autoConnect) this.connect();
  });
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

  /** Opens like the server does: the stream goes live, then says hello. */
  connect(resumed = false, id: string | null = null): void {
    this.options.onStatus('live');
    this.hello(resumed, id);
  }

  hello(resumed = false, id: string | null = null): void {
    this.emit({ event: 'hello', data: JSON.stringify({ expires_in: 900, resumed }), id });
  }

  static reset(): void {
    FakeEventStreamClient.instances = [];
    FakeEventStreamClient.autoConnect = true;
  }
}

export { FakeEventStreamClient as EventStreamClient };
