/**
 * A small server-sent events client over fetch (EventSource cannot send the bearer
 * token). Frames are parsed from the byte stream; the connection reconnects with
 * backoff and asks for a fresh token when the server says goodbye.
 */
import { SseFrameBuffer } from './sseBuffer';

export interface SseMessage {
  event: string;
  data: string;
  id: string | null;
}

export type StreamStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

export interface StreamOptions {
  url: string;
  /** Returns a usable access token, refreshing when asked, or null when signed out. */
  getToken: (refresh: boolean) => Promise<string | null>;
  onMessage: (message: SseMessage) => void;
  onStatus: (status: StreamStatus) => void;
  fetchImpl?: typeof fetch;
  minBackoffMs?: number;
  maxBackoffMs?: number;
}

/** Splits complete frames (blank-line terminated) off the front of `buffer`. */
export function parseSseFrames(buffer: string): { messages: SseMessage[]; rest: string } {
  const normalised = buffer.replace(/\r\n/g, '\n');
  const parts = normalised.split('\n\n');
  const rest = parts.pop() ?? '';
  const messages: SseMessage[] = [];
  for (const frame of parts) {
    const message: SseMessage = { event: 'message', data: '', id: null };
    const dataLines: string[] = [];
    for (const line of frame.split('\n')) {
      if (line.startsWith(':') || line.trim() === '') continue;
      const colon = line.indexOf(':');
      const field = colon === -1 ? line : line.slice(0, colon);
      const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '');
      if (field === 'event') message.event = value;
      else if (field === 'data') dataLines.push(value);
      else if (field === 'id') message.id = value;
    }
    if (dataLines.length > 0 || message.event !== 'message') {
      message.data = dataLines.join('\n');
      messages.push(message);
    }
  }
  return { messages, rest };
}

export class EventStreamClient {
  private controller: AbortController | null = null;
  private running = false;
  private attempts = 0;

  constructor(private readonly options: StreamOptions) {}

  start(): void {
    if (this.running) return;
    this.running = true;
    void this.loop();
  }

  stop(): void {
    this.running = false;
    this.controller?.abort();
    this.controller = null;
    this.options.onStatus('offline');
  }

  private async loop(): Promise<void> {
    let refresh = false;
    while (this.running) {
      this.options.onStatus(this.attempts === 0 ? 'connecting' : 'reconnecting');
      const token = await this.options.getToken(refresh);
      // stop() may have run while the token was being fetched; never open a stream after it.
      if (this.stopped()) return;
      if (token === null) {
        this.running = false;
        this.options.onStatus('offline');
        return;
      }
      const outcome = await this.connect(token);
      if (this.stopped()) return;
      refresh = outcome === 'unauthorised' || outcome === 'bye';
      if (outcome === 'bye') {
        this.attempts = 0;
        continue;
      }
      this.attempts += 1;
      await this.delay(this.backoffMs());
    }
  }

  private async connect(token: string): Promise<'ended' | 'bye' | 'unauthorised' | 'failed'> {
    const controller = new AbortController();
    this.controller = controller;
    const fetchImpl = this.options.fetchImpl ?? fetch;
    try {
      const response = await fetchImpl(this.options.url, {
        headers: { Accept: 'text/event-stream', Authorization: `Bearer ${token}` },
        credentials: 'include',
        signal: controller.signal,
      });
      if (response.status === 401) return 'unauthorised';
      if (!response.ok || response.body === null) return 'failed';
      this.options.onStatus('live');
      return await this.consume(response.body, controller.signal);
    } catch {
      return this.running ? 'failed' : 'ended';
    } finally {
      controller.abort();
      this.controller = null;
    }
  }

  private async consume(
    body: ReadableStream<Uint8Array>,
    signal: AbortSignal,
  ): Promise<'ended' | 'bye'> {
    const reader = body.getReader();
    const buffer = new SseFrameBuffer();
    const cancel = () => {
      void reader.cancel().catch(() => undefined);
    };
    signal.addEventListener('abort', cancel, { once: true });
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done || signal.aborted || this.stopped()) return 'ended';
        for (const frame of buffer.push(value)) {
          for (const message of parseSseFrames(frame).messages) {
            if (this.stopped()) return 'ended';
            if (message.event === 'bye') return 'bye';
            this.attempts = 0;
            this.options.onMessage(message);
          }
        }
      }
    } finally {
      signal.removeEventListener('abort', cancel);
      await reader.cancel().catch(() => undefined);
      reader.releaseLock();
    }
  }

  /** Read through a method so the flag is re-read after each await. */
  private stopped(): boolean {
    return !this.running;
  }

  private backoffMs(): number {
    const min = this.options.minBackoffMs ?? 1_000;
    const max = this.options.maxBackoffMs ?? 30_000;
    return Math.min(max, min * 2 ** Math.max(0, this.attempts - 1));
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(resolve, ms);
    });
  }
}
