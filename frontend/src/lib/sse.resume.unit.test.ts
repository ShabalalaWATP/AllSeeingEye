import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  EventStreamClient,
  jitteredBackoffMs,
  parseSseFrames,
  STREAM_IDLE_TIMEOUT_MS,
} from './sse';

const encoder = new TextEncoder();

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

/** A response body the test writes to by hand and never closes. */
function openStream() {
  let push: (chunk: string) => void = () => undefined;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      push = (chunk) => {
        controller.enqueue(encoder.encode(chunk));
      };
    },
  });
  return { body, push: (chunk: string) => push(chunk) };
}

function headersOf(init: RequestInit | undefined): Record<string, string> {
  return init?.headers as Record<string, string>;
}

function client(
  fetchImpl: typeof fetch,
  extra: Partial<ConstructorParameters<typeof EventStreamClient>[0]> = {},
) {
  return new EventStreamClient({
    url: '/api/stream',
    fetchImpl,
    minBackoffMs: 1_000,
    maxBackoffMs: 4_000,
    random: () => 0,
    getToken: () => Promise.resolve('token'),
    onMessage: () => undefined,
    onStatus: () => undefined,
    ...extra,
  });
}

afterEach(() => {
  vi.useRealTimers();
});

describe('jittered backoff', () => {
  it('stays between zero and the capped exponential step', () => {
    for (let attempts = 0; attempts <= 12; attempts += 1) {
      const step = Math.min(30_000, 1_000 * 2 ** Math.max(0, attempts - 1));
      expect(jitteredBackoffMs(attempts, 1_000, 30_000, () => 0)).toBe(0);
      const high = jitteredBackoffMs(attempts, 1_000, 30_000, () => 0.999_999);
      expect(high).toBeLessThan(step);
      expect(high).toBeGreaterThanOrEqual(step - 1);
    }
    expect(jitteredBackoffMs(3, 1_000, 30_000, () => 0.5)).toBe(2_000);
  });

  it('waits the jittered delay before retrying', async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn(() => Promise.resolve(new Response(null, { status: 503 })));
    const failing = client(fetchImpl, { random: () => 0.5 });
    failing.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(499);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    // The second failure doubles the step to 2 seconds, so half of it is 1 second.
    await vi.advanceTimersByTimeAsync(999);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    failing.stop();
  });
});

describe('resuming', () => {
  it('records ids from every frame, including id-only frames', () => {
    const parsed = parseSseFrames('id: ab-1\nevent: hello\ndata: {}\n\nid: ab-2\n\n: ping\n\n');
    expect(parsed.messages).toEqual([{ event: 'hello', data: '{}', id: 'ab-1' }]);
    expect(parsed.lastEventId).toBe('ab-2');
    expect(parseSseFrames(': ping\n\n').lastEventId).toBeNull();
  });

  it('sends the last frame id when it reconnects', async () => {
    const bodies = [
      ['id: ab-1\nevent: hello\ndata: {}\n\nid: ab-2\n\n', 'id: ab-3\nevent: bye\ndata: {}\n\n'],
      ['id: ab-4\nevent: hello\ndata: {}\n\n'],
      ['id: \nevent: hello\ndata: {}\n\n'],
      [`id: ${'x'.repeat(65)}\nevent: hello\ndata: {}\n\n`],
      ['event: hello\ndata: {}\n\n'],
    ];
    const sent: (string | undefined)[] = [];
    const fetchImpl = vi.fn((_: RequestInfo | URL, init?: RequestInit) => {
      sent.push(headersOf(init)['Last-Event-ID']);
      const body = bodies.shift();
      return Promise.resolve(new Response(streamOf(body ?? []), { status: 200 }));
    });
    const messages: string[] = [];
    const resuming = client(fetchImpl, {
      minBackoffMs: 1,
      maxBackoffMs: 1,
      onMessage: (message) => messages.push(message.id ?? 'none'),
    });
    resuming.start();
    await vi.waitFor(() => {
      expect(sent.length).toBeGreaterThanOrEqual(6);
    });
    resuming.stop();
    // Empty and oversized ids reset the position; a frame without an id keeps it.
    expect(sent.slice(0, 6)).toEqual([undefined, 'ab-3', 'ab-4', undefined, undefined, undefined]);
    expect(messages.slice(0, 3)).toEqual(['ab-1', 'ab-4', '']);
  });
});

describe('idle timeout', () => {
  it('reconnects when a live stream falls silent, counting pings as activity', async () => {
    vi.useFakeTimers();
    const streams: ReturnType<typeof openStream>[] = [];
    const statuses: string[] = [];
    const fetchImpl = vi.fn(() => {
      const stream = openStream();
      streams.push(stream);
      return Promise.resolve(new Response(stream.body, { status: 200 }));
    });
    const watched = client(fetchImpl, { onStatus: (status) => statuses.push(status) });
    watched.start();
    await vi.advanceTimersByTimeAsync(40_000);
    streams[0]!.push(': ping\n\n');
    await vi.advanceTimersByTimeAsync(STREAM_IDLE_TIMEOUT_MS - 1);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    // The idle abort fires at 45 seconds; a zero-jitter retry follows a tick later.
    await vi.advanceTimersByTimeAsync(2);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(statuses).toEqual(['connecting', 'live', 'reconnecting', 'live']);
    watched.stop();
  });

  it('gives up on a request that never answers', async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn(
      (_: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('aborted', 'AbortError'));
          });
        }),
    );
    const hanging = client(fetchImpl, { idleTimeoutMs: 10_000 });
    hanging.start();
    await vi.advanceTimersByTimeAsync(9_999);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(2);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    hanging.stop();
  });
});
