import { webcrypto } from 'node:crypto';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import {
  clearBrowserPush,
  currentPush,
  disablePush,
  enablePush,
  endpointHash,
  pushRecord,
  rememberPush,
} from './browserPush';

const registered = vi.fn();
const removed = vi.fn();
beforeEach(() => {
  registered.mockClear();
  removed.mockClear();
  server.use(
    http.post('/api/me/notifications/push', async ({ request }) => {
      registered(await request.json());
      return HttpResponse.json({ id: 'new', endpoint_hash: 'new-hash', created_at: 'now' });
    }),
    http.delete('/api/me/notifications/push/:id', ({ params }) => {
      removed(params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  vi.stubGlobal('crypto', webcrypto);
});
afterEach(() => vi.unstubAllGlobals());

function browser(keys: Record<string, string> = { p256dh: 'key', auth: 'secret' }) {
  const subscription = {
    endpoint: 'https://fcm.googleapis.com/synthetic-device',
    unsubscribe: vi.fn().mockResolvedValue(true),
    toJSON: () => ({ keys }),
  };
  const manager = {
    getSubscription: vi.fn<() => Promise<typeof subscription | null>>().mockResolvedValue(null),
    subscribe: vi.fn().mockResolvedValue(subscription),
  };
  const registration = { pushManager: manager };
  const serviceWorker = {
    register: vi.fn().mockResolvedValue(registration),
    ready: Promise.resolve(registration),
    getRegistration: vi.fn().mockResolvedValue(registration),
  };
  vi.stubGlobal('isSecureContext', true);
  vi.stubGlobal('PushManager', vi.fn());
  vi.stubGlobal('Notification', { requestPermission: vi.fn().mockResolvedValue('granted') });
  vi.stubGlobal('navigator', { serviceWorker });
  return { subscription, manager, serviceWorker };
}

it('refuses unsupported browsers and treats a missing worker registration as unsubscribed', async () => {
  const { serviceWorker } = browser();
  vi.stubGlobal('isSecureContext', false);
  await expect(enablePush('BA', [], 'user-a')).rejects.toThrow('Push is unsupported');
  expect(serviceWorker.register).not.toHaveBeenCalled();
  vi.stubGlobal('isSecureContext', true);
  serviceWorker.getRegistration.mockResolvedValue(undefined);
  expect(await currentPush()).toBeNull();
});

it.each([true, false])('replaces a browser subscription with a %s server match', async (known) => {
  const { subscription, manager } = browser();
  manager.getSubscription.mockResolvedValue(subscription);
  const hash = await endpointHash(subscription as unknown as PushSubscription);
  const previous = {
    id: 'previous',
    endpoint_hash: known ? hash : 'another-hash',
    created_at: 'now',
  };
  await enablePush('BA', [previous], 'user-a');
  if (known) {
    expect(removed).toHaveBeenCalledWith('previous');
    expect(removed.mock.invocationCallOrder[0]).toBeLessThan(
      subscription.unsubscribe.mock.invocationCallOrder[0]!,
    );
  } else {
    expect(removed).not.toHaveBeenCalled();
  }
  expect(subscription.unsubscribe).toHaveBeenCalledOnce();
  expect(subscription.unsubscribe.mock.invocationCallOrder[0]).toBeLessThan(
    manager.subscribe.mock.invocationCallOrder[0]!,
  );
  expect(registered).toHaveBeenCalledWith({
    endpoint: subscription.endpoint,
    p256dh: 'key',
    auth: 'secret',
  });
});

const incompleteKeys: Record<string, string>[] = [{}, { p256dh: 'key' }];
it.each(incompleteKeys)(
  'discards a newly created subscription with incomplete keys %j',
  async (keys) => {
    const { subscription } = browser(keys);
    await expect(enablePush('BA', [], 'user-a')).rejects.toThrow('incomplete push keys');
    expect(registered).not.toHaveBeenCalled();
    expect(subscription.unsubscribe).toHaveBeenCalledOnce();
  },
);

it.each([true, false])(
  'removes the local browser only when the server device matches: %s',
  async (matches) => {
    const { subscription, manager } = browser();
    manager.getSubscription.mockResolvedValue(subscription);
    const hash = await endpointHash(subscription as unknown as PushSubscription);
    await disablePush({
      id: 'selected',
      endpoint_hash: matches ? hash : 'another-browser',
      created_at: 'now',
    });
    expect(removed).toHaveBeenCalledWith('selected');
    expect(subscription.unsubscribe).toHaveBeenCalledTimes(matches ? 1 : 0);
  },
);

it('records which account opted this browser in, and forgets it when push is removed', async () => {
  const { subscription, manager } = browser();
  await enablePush('BA', [], 'user-a');
  expect(pushRecord()).toEqual({ owner: 'user-a', hash: 'new-hash' });
  manager.getSubscription.mockResolvedValue(subscription);
  const hash = await endpointHash(subscription as unknown as PushSubscription);
  await disablePush({ id: 'new', endpoint_hash: hash, created_at: 'now' });
  expect(pushRecord()).toBeNull();
  rememberPush('user-a', hash);
  await clearBrowserPush();
  expect(pushRecord()).toBeNull();
});
