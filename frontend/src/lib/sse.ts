/**
 * A small server-sent events client over fetch (EventSource cannot send the bearer
 * token). Frames are parsed from the byte stream; the connection reconnects with
 * jittered backoff, resumes from the last frame id it saw, and asks for a fresh
 * token when the server says goodbye. A silent connection is treated as dead.
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
  /** Abort and reconnect when nothing, not even a keep-alive ping, arrives for this long. */
  idleTimeoutMs?: number;
  /** A number in [0, 1) that spreads retries; Math.random unless a test supplies one. */
  random?: () => number;
}

/** Three missed 15-second server pings. */
export const STREAM_IDLE_TIMEOUT_MS = 45_000;
/** Only short, printable ids are sent back; anything else starts afresh. */
const RESUMABLE_ID = /^[\x21-\x7E]{1,64}$/;

type Outcome = 'ended' | 'bye' | 'unauthorised' | 'failed';

/** Splits complete frames (blank-line terminated) off the front of `buffer`. */
export function parseSseFrames(buffer: string): {
  messages: SseMessage[];
  rest: string;
  /** The id of the last complete frame that set one, including frames with no data. */
  lastEventId: string | null;
} {
  const normalised = buffer.replace(/\r\n/g, '\n');
  const parts = normalised.split('\n\n');
  const rest = parts.pop() ?? '';
  const messages: SseMessage[] = [];
  let lastEventId: string | null = null;
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
    if (message.id !== null) lastEventId = message.id;
    if (dataLines.length > 0 || message.event !== 'message') {
      message.data = dataLines.join('\n');
      messages.push(message);
    }
  }
  return { messages, rest, lastEventId };
}

/** Exponential backoff with full jitter: uniformly between zero and the capped step. */
export function jitteredBackoffMs(
  attempts: number,
  minMs: number,
  maxMs: number,
  random: () => number,
): number {
  const step = Math.min(maxMs, minMs * 2 ** Math.max(0, attempts - 1));
  return Math.floor(random() * step);
}

export class EventStreamClient {
  private controller: AbortController | null = null;
  private running = false;
  private attempts = 0;
  private lastEventId: string | null = null;

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
      // Spread retries so a server restart does not bring every browser back at once.
      await this.delay(
        jitteredBackoffMs(
          this.attempts,
          this.options.minBackoffMs ?? 1_000,
          this.options.maxBackoffMs ?? 30_000,
          this.options.random ?? Math.random,
        ),
      );
    }
  }

  private async connect(token: string): Promise<Outcome> {
    const controller = new AbortController();
    this.controller = controller;
    const fetchImpl = this.options.fetchImpl ?? fetch;
    const idleMs = this.options.idleTimeoutMs ?? STREAM_IDLE_TIMEOUT_MS;
    const idle: { timer?: ReturnType<typeof setTimeout> } = {};
    const touch = () => {
      clearTimeout(idle.timer);
      idle.timer = setTimeout(() => {
        controller.abort();
      }, idleMs);
    };
    const headers: Record<string, string> = {
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
    };
    // The server replays what this browser missed when the id is still in its window.
    if (this.lastEventId !== null) headers['Last-Event-ID'] = this.lastEventId;
    try {
      touch();
      const response = await fetchImpl(this.options.url, {
        headers,
        credentials: 'include',
        signal: controller.signal,
      });
      if (response.status === 401) return 'unauthorised';
      if (!response.ok || response.body === null) return 'failed';
      this.options.onStatus('live');
      return await this.consume(response.body, controller.signal, touch);
    } catch {
      return this.running ? 'failed' : 'ended';
    } finally {
      clearTimeout(idle.timer);
      controller.abort();
      this.controller = null;
    }
  }

  private async consume(
    body: ReadableStream<Uint8Array>,
    signal: AbortSignal,
    touch: () => void,
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
        touch();
        for (const frame of buffer.push(value)) {
          const parsed = parseSseFrames(frame);
          if (parsed.lastEventId !== null) this.remember(parsed.lastEventId);
          for (const message of parsed.messages) {
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

  private remember(id: string): void {
    this.lastEventId = RESUMABLE_ID.test(id) ? id : null;
  }

  /** Read through a method so the flag is re-read after each await. */
  private stopped(): boolean {
    return !this.running;
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(resolve, ms);
    });
  }
}
