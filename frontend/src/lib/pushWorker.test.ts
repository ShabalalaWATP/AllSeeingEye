import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { expect, it, vi } from 'vitest';

it('handles only push and click, with generic visible text and a same-origin target', async () => {
  const handlers = new Map<string, (event: unknown) => void>();
  const showNotification = vi.fn().mockResolvedValue(undefined);
  const openWindow = vi.fn().mockResolvedValue(undefined);
  const source = readFileSync('public/push-worker.js', 'utf8');
  runInNewContext(source, {
    URL,
    self: {
      addEventListener: (kind: string, fn: (event: unknown) => void) => handlers.set(kind, fn),
      registration: { showNotification },
      clients: { openWindow },
      location: { origin: 'https://app.example' },
    },
  });
  expect([...handlers.keys()]).toEqual(['push', 'notificationclick']);
  const id = '11111111-1111-4111-8111-111111111111';
  let pending: Promise<void> | undefined;
  const waitUntil = (value: Promise<void>) => {
    pending = value;
  };
  handlers.get('push')?.({ data: { text: () => id }, waitUntil });
  await pending;
  expect(showNotification).toHaveBeenCalledWith(
    'New alert',
    expect.objectContaining({ body: 'Open the app to view this alert securely.', data: { id } }),
  );
  handlers.get('notificationclick')?.({
    notification: { close: vi.fn(), data: { id } },
    waitUntil,
  });
  await pending;
  expect(openWindow).toHaveBeenCalledWith(`https://app.example/warning?alert=${id}`);
  handlers.get('notificationclick')?.({
    notification: { close: vi.fn(), data: { id: 'https://evil.example' } },
    waitUntil,
  });
  expect(openWindow).toHaveBeenCalledOnce();
});
