import { afterEach, describe, expect, it, vi } from 'vitest';

import { EventStreamClient, parseSseFrames } from './sse';
import type { SseMessage, StreamStatus } from './sse';

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

describe('parseSseFrames', () => {
  it('splits complete frames and keeps the remainder', () => {
    const { messages, rest } = parseSseFrames(
      'event: hello\ndata: {"a":1}\n\n: comment\r\n\r\nid: 7\ndata: one\ndata: two\n\nevent: partial\ndata: x',
    );
    expect(messages).toEqual([
      { event: 'hello', data: '{"a":1}', id: null },
      { event: 'message', data: 'one\ntwo', id: '7' },
    ]);
    expect(rest).toBe('event: partial\ndata: x');
  });

  it('accepts fields without a colon and strips one leading space', () => {
    const { messages } = parseSseFrames('data\n\nevent:  spaced\ndata:  two spaces\n\n');
    expect(messages[0]).toEqual({ event: 'message', data: '', id: null });
    expect(messages[1]).toEqual({ event: ' spaced', data: ' two spaces', id: null });
  });
});

describe('EventStreamClient', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('delivers messages, reconnects on goodbye with a refreshed token and stops', async () => {
    const calls: { token: string | null }[] = [];
    const responses = [
      () =>
        new Response(
          streamOf([
            'event: hello\ndata: {}\n\nevent: event.upsert\n',
            'data: {"events":[]}\n\nevent: bye\ndata: {}\n\n',
          ]),
          {
            status: 200,
            headers: { 'Content-Type': 'text/event-stream' },
          },
        ),
      () => new Response(streamOf(['event: hello\ndata: {}\n\n']), { status: 200 }),
    ];
    const fetchImpl = vi.fn((_: RequestInfo | URL, init?: RequestInit) => {
      const headers = init?.headers as Record<string, string>;
      calls.push({ token: headers.Authorization ?? null });
      const next = responses.shift();
      return Promise.resolve(next ? next() : new Response(streamOf([]), { status: 200 }));
    });
    const messages: SseMessage[] = [];
    const statuses: StreamStatus[] = [];
    let refreshes = 0;
    const client = new EventStreamClient({
      url: '/api/stream',
      fetchImpl,
      minBackoffMs: 1,
      maxBackoffMs: 2,
      getToken: (refresh) => {
        if (refresh) refreshes += 1;
        return Promise.resolve(refresh ? 'fresh' : 'first');
      },
      onMessage: (message) => messages.push(message),
      onStatus: (status) => statuses.push(status),
    });
    client.start();
    await vi.waitFor(() => {
      expect(calls.length).toBeGreaterThanOrEqual(2);
    });
    client.stop();
    expect(messages.map((m) => m.event)).toEqual(['hello', 'event.upsert', 'hello']);
    expect(calls[0]?.token).toBe('Bearer first');
    expect(calls[1]?.token).toBe('Bearer fresh');
    expect(refreshes).toBe(1);
    expect(statuses[0]).toBe('connecting');
    expect(statuses).toContain('live');
    expect(statuses.at(-1)).toBe('offline');
  });

  it('goes offline when no token is available and backs off after failures', async () => {
    const statuses: StreamStatus[] = [];
    const signedOut = new EventStreamClient({
      url: '/api/stream',
      getToken: () => Promise.resolve(null),
      onMessage: () => undefined,
      onStatus: (status) => statuses.push(status),
    });
    signedOut.start();
    await vi.waitFor(() => {
      expect(statuses.at(-1)).toBe('offline');
    });

    const attempts: number[] = [];
    const failing = new EventStreamClient({
      url: '/api/stream',
      fetchImpl: () => {
        attempts.push(Date.now());
        return Promise.resolve(new Response(null, { status: 503 }));
      },
      minBackoffMs: 1,
      maxBackoffMs: 4,
      getToken: () => Promise.resolve('token'),
      onMessage: () => undefined,
      onStatus: () => undefined,
    });
    failing.start();
    await vi.waitFor(() => {
      expect(attempts.length).toBeGreaterThanOrEqual(3);
    });
    failing.stop();
    failing.start();
    failing.stop();
  });

  it('never opens a stream when stopped while the token is being fetched', async () => {
    const fetchImpl = vi.fn();
    let release: (token: string | null) => void = () => undefined;
    const client = new EventStreamClient({
      url: '/api/stream',
      fetchImpl,
      getToken: () =>
        new Promise<string | null>((resolve) => {
          release = resolve;
        }),
      onMessage: () => undefined,
      onStatus: () => undefined,
    });
    client.start();
    client.stop();
    release('late-token');
    await Promise.resolve();
    await Promise.resolve();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('treats a 401 as a request for a refreshed token', async () => {
    const tokens: boolean[] = [];
    let served = 0;
    const client = new EventStreamClient({
      url: '/api/stream',
      fetchImpl: () => {
        served += 1;
        return Promise.resolve(
          served === 1
            ? new Response(null, { status: 401 })
            : new Response(streamOf([]), { status: 200 }),
        );
      },
      minBackoffMs: 1,
      getToken: (refresh) => {
        tokens.push(refresh);
        return Promise.resolve('t');
      },
      onMessage: () => undefined,
      onStatus: () => undefined,
    });
    client.start();
    await vi.waitFor(() => {
      expect(tokens.length).toBeGreaterThanOrEqual(2);
    });
    client.stop();
    expect(tokens[0]).toBe(false);
    expect(tokens[1]).toBe(true);
  });
});
