import { expect, it, vi } from 'vitest';
import { MAX_SSE_FRAME_BYTES, SseFrameBuffer } from './sseBuffer';
import { EventStreamClient, parseSseFrames } from './sse';

it('preserves UTF-8 and CRLF across every byte boundary, with multiple frames per chunk', () => {
  const buffer = new SseFrameBuffer();
  const text = 'event: test\r\ndata: Москва 北京\r\n\r\ndata: next\n\n';
  const frames: string[] = [];
  for (const byte of new TextEncoder().encode(text))
    frames.push(...buffer.push(new Uint8Array([byte])));
  expect(
    frames.flatMap((frame) => parseSseFrames(frame).messages).map((item) => item.data),
  ).toEqual(['Москва 北京', 'next']);
  expect([...buffer.push(new TextEncoder().encode('data: a\n\ndata: b\n\n'))]).toHaveLength(2);
});

it('bounds an unterminated frame across many chunks', () => {
  const buffer = new SseFrameBuffer();
  const chunk = new Uint8Array(1024).fill(65);
  for (let i = 0; i < MAX_SSE_FRAME_BYTES / chunk.length; i++)
    expect([...buffer.push(chunk)]).toEqual([]);
  expect(() => [...buffer.push(chunk)]).toThrow('byte limit');
});

it('cancels an oversized response, releases its lock and backs off before reconnecting', async () => {
  vi.useFakeTimers();
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(MAX_SSE_FRAME_BYTES + 1).fill(65));
    },
    cancel,
  });
  const fetchImpl = vi
    .fn()
    .mockResolvedValueOnce(new Response(body))
    .mockResolvedValue(new Response(null, { status: 503 }));
  const client = new EventStreamClient({
    url: '/api/stream',
    fetchImpl,
    getToken: () => Promise.resolve('test'),
    onMessage: vi.fn(),
    onStatus: vi.fn(),
  });
  try {
    client.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(cancel).toHaveBeenCalledOnce();
    expect(body.locked).toBe(false);
    expect(fetchImpl).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  } finally {
    client.stop();
    vi.useRealTimers();
  }
});

it('cancels an idle reader immediately on stop, even when fetch does not honour its signal', async () => {
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({ cancel });
  const client = new EventStreamClient({
    url: '/api/stream',
    fetchImpl: vi.fn().mockResolvedValue(new Response(body)),
    getToken: () => Promise.resolve('test'),
    onMessage: vi.fn(),
    onStatus: vi.fn(),
  });
  client.start();
  await vi.waitFor(() => expect(body.locked).toBe(true));
  client.stop();
  await vi.waitFor(() => expect(body.locked).toBe(false));
  expect(cancel).toHaveBeenCalledOnce();
});
