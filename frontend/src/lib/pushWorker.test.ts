import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it, vi } from 'vitest';

const id = '11111111-1111-4111-8111-111111111111';
const target = `https://app.example/warning?alert=${id}`;

interface FakeWindow {
  url: string;
  focus: ReturnType<typeof vi.fn>;
  navigate: ReturnType<typeof vi.fn>;
  postMessage: ReturnType<typeof vi.fn>;
}

function windowClient(url: string, navigate = vi.fn()): FakeWindow {
  const client: FakeWindow = {
    url,
    focus: vi.fn(),
    navigate,
    postMessage: vi.fn(),
  };
  client.focus.mockResolvedValue(client);
  return client;
}

function loadWorker(windows: FakeWindow[] = [], subscription: unknown = null) {
  const handlers = new Map<string, (event: unknown) => void>();
  const showNotification = vi.fn().mockResolvedValue(undefined);
  const openWindow = vi.fn().mockResolvedValue(undefined);
  const matchAll = vi.fn().mockResolvedValue(windows);
  const pushManager = {
    getSubscription: vi.fn().mockResolvedValue(subscription),
    subscribe: vi.fn().mockResolvedValue({ endpoint: 'https://push.example/new' }),
  };
  runInNewContext(readFileSync('public/push-worker.js', 'utf8'), {
    URL,
    self: {
      addEventListener: (kind: string, fn: (event: unknown) => void) => handlers.set(kind, fn),
      registration: { showNotification, pushManager },
      clients: { openWindow, matchAll },
      location: { origin: 'https://app.example' },
    },
  });
  let pending: Promise<unknown> | undefined;
  const dispatch = async (kind: string, event: object) => {
    handlers.get(kind)?.({
      ...event,
      waitUntil: (value: Promise<unknown>) => {
        pending = value;
      },
    });
    await pending;
  };
  const click = (data: unknown) =>
    dispatch('notificationclick', { notification: { close: vi.fn(), data } });
  return { handlers, showNotification, openWindow, matchAll, pushManager, dispatch, click };
}

describe('push worker', () => {
  it('handles only push, click and renewal, with generic visible text', async () => {
    const worker = loadWorker();
    expect([...worker.handlers.keys()]).toEqual([
      'push',
      'notificationclick',
      'pushsubscriptionchange',
    ]);
    await worker.dispatch('push', { data: { text: () => id } });
    expect(worker.showNotification).toHaveBeenCalledWith(
      'New alert',
      expect.objectContaining({ body: 'Open the app to view this alert securely.', data: { id } }),
    );
    worker.handlers.get('push')?.({ data: { text: () => 'not an id' }, waitUntil: vi.fn() });
    expect(worker.showNotification).toHaveBeenCalledOnce();
  });

  it('opens a window only when no app window is open, and ignores unsafe ids', async () => {
    const worker = loadWorker([windowClient('https://elsewhere.example/')]);
    await worker.click({ id });
    expect(worker.matchAll).toHaveBeenCalledWith({ type: 'window', includeUncontrolled: true });
    expect(worker.openWindow).toHaveBeenCalledWith(target);
    await worker.click({ id: 'https://evil.example' });
    expect(worker.openWindow).toHaveBeenCalledOnce();
  });

  it('focuses and navigates an open app window instead of opening another', async () => {
    const open = windowClient('https://app.example/reports');
    const worker = loadWorker([open]);
    await worker.click({ id });
    expect(open.focus).toHaveBeenCalledOnce();
    expect(open.navigate).toHaveBeenCalledWith(target);
    expect(worker.openWindow).not.toHaveBeenCalled();
  });

  it('falls back to a new window when the open one cannot be navigated', async () => {
    const open = windowClient(
      'https://app.example/',
      vi.fn().mockRejectedValue(new TypeError('Not controlled')),
    );
    const worker = loadWorker([open]);
    await worker.click({ id });
    expect(open.focus).toHaveBeenCalledOnce();
    expect(worker.openWindow).toHaveBeenCalledWith(target);
  });

  it('subscribes again with the previous key and tells open windows', async () => {
    const open = windowClient('https://app.example/');
    const worker = loadWorker([open]);
    const key = new Uint8Array([4, 1, 2]);
    await worker.dispatch('pushsubscriptionchange', {
      oldSubscription: { options: { applicationServerKey: key } },
      newSubscription: null,
    });
    expect(worker.pushManager.subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: key,
    });
    expect(open.postMessage).toHaveBeenCalledWith({ type: 'push-subscription-changed' });
  });

  it('keeps a replacement the browser already made, and cannot subscribe without a key', async () => {
    const renewed = loadWorker([], { endpoint: 'https://push.example/renewed' });
    await renewed.dispatch('pushsubscriptionchange', { oldSubscription: null });
    expect(renewed.pushManager.subscribe).not.toHaveBeenCalled();
    const supplied = loadWorker();
    await supplied.dispatch('pushsubscriptionchange', {
      newSubscription: { endpoint: 'https://push.example/supplied' },
    });
    expect(supplied.pushManager.getSubscription).not.toHaveBeenCalled();
    expect(supplied.pushManager.subscribe).not.toHaveBeenCalled();
    const keyless = loadWorker();
    await keyless.dispatch('pushsubscriptionchange', {});
    expect(keyless.pushManager.subscribe).not.toHaveBeenCalled();
  });
});
