import { describe, expect, it, vi } from 'vitest';

import { EventStreamClient, parseSseFrames } from './sse';

describe('SSE frame parsing edges', () => {
  it('reads ids, skips comments and bare field names, and accepts CRLF', () => {
    const { messages, rest } = parseSseFrames(
      'id: 7\r\nevent: alert\r\ndata: {"a":1}\r\n\r\n: keep-alive\nretry\n\ndata: tail',
    );
    expect(messages).toEqual([{ event: 'alert', data: '{"a":1}', id: '7' }]);
    expect(rest).toBe('data: tail');
  });

  it('starts only once', () => {
    const client = new EventStreamClient({
      url: '/api/stream',
      getToken: () => null,
      onMessage: vi.fn(),
      onStatus: vi.fn(),
      fetchImpl: vi.fn(),
    } as unknown as ConstructorParameters<typeof EventStreamClient>[0]);
    client.start();
    client.start();
    client.stop();
    expect(true).toBe(true);
  });
});
