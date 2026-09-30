import { afterEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { clearBrowserPush, disablePush, enablePush } from './browserPush';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function browser(permission: NotificationPermission = 'granted') {
  const unsubscribe = vi.fn().mockResolvedValue(true);
  const subscription = {
    endpoint: 'https://fcm.googleapis.com/test',
    unsubscribe,
    toJSON: () => ({ keys: { p256dh: 'public', auth: 'auth' } }),
  };
  const subscribe = vi.fn().mockResolvedValue(subscription);
  const requestPermission = vi.fn().mockResolvedValue(permission);
  const registration = {
    pushManager: { subscribe, getSubscription: vi.fn().mockResolvedValue(null) },
  };
  vi.stubGlobal('isSecureContext', true);
  vi.stubGlobal('PushManager', vi.fn());
  vi.stubGlobal('Notification', { requestPermission });
  vi.stubGlobal('navigator', {
    serviceWorker: {
      register: vi.fn().mockResolvedValue(registration),
      ready: Promise.resolve(registration),
      getRegistration: vi.fn().mockResolvedValue(registration),
    },
  });
  return { requestPermission, subscription, registration, subscribe, unsubscribe };
}

it('requests permission from the gesture then registers only endpoint keys', async () => {
  const { requestPermission, subscribe } = browser();
  const requests: unknown[] = [];
  server.use(
    http.post('/api/me/notifications/push', async ({ request }) => {
      requests.push(await request.json());
      return HttpResponse.json({ id: 'device', endpoint_hash: 'hash', created_at: 'now' });
    }),
  );
  const result = enablePush('BA', []);
  expect(requestPermission).toHaveBeenCalledOnce();
  await result;
  expect(subscribe).toHaveBeenCalledWith({
    userVisibleOnly: true,
    applicationServerKey: expect.any(Uint8Array),
  });
  expect(requests).toEqual([
    {
      endpoint: 'https://fcm.googleapis.com/test',
      p256dh: 'public',
      auth: 'auth',
    },
  ]);
});

it('denied permission never creates a subscription', async () => {
  const { subscribe } = browser('denied');
  await expect(enablePush('BA', [])).rejects.toThrow(/permission/);
  expect(subscribe).not.toHaveBeenCalled();
});

it('failed server registration unsubscribes the browser', async () => {
  const { unsubscribe } = browser();
  server.use(
    http.post('/api/me/notifications/push', () => new HttpResponse(null, { status: 422 })),
  );
  await expect(enablePush('BA', [])).rejects.toThrow();
  expect(unsubscribe).toHaveBeenCalledOnce();
});

it('removes server subscription before browser cleanup and signs out locally', async () => {
  const { registration, subscription, unsubscribe } = browser();
  const removed = vi.fn();
  server.use(
    http.delete('/api/me/notifications/push/device', () => {
      removed();
      return new HttpResponse(null, { status: 204 });
    }),
  );
  await disablePush({ id: 'device', endpoint_hash: 'hash', created_at: 'now' });
  expect(removed).toHaveBeenCalledOnce();
  registration.pushManager.getSubscription.mockResolvedValue(subscription);
  await clearBrowserPush();
  expect(unsubscribe).toHaveBeenCalledOnce();
});
