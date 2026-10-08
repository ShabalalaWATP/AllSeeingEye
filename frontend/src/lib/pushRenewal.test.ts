import { webcrypto } from 'node:crypto';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { server } from '@/test/server';

import { clearBrowserPush, endpointHash, pushRecord, rememberPush } from './browserPush';
import { renewPush } from './pushRenewal';

const registered = vi.fn();
const removed = vi.fn();
let publicKey: string | null = 'BA';

function subscriptionFor(endpoint: string) {
  return {
    endpoint,
    unsubscribe: vi.fn().mockResolvedValue(true),
    toJSON: () => ({ keys: { p256dh: 'key', auth: 'secret' } }),
  };
}
type Subscription = ReturnType<typeof subscriptionFor>;
const hashOf = (subscription: Subscription) =>
  endpointHash(subscription as unknown as PushSubscription);

function browser(current: Subscription | null, permission = 'granted') {
  const created = subscriptionFor('https://push.example/created');
  const manager = {
    getSubscription: vi.fn().mockResolvedValue(current),
    subscribe: vi.fn().mockResolvedValue(created),
  };
  vi.stubGlobal('isSecureContext', true);
  vi.stubGlobal('PushManager', vi.fn());
  vi.stubGlobal('Notification', { permission });
  vi.stubGlobal('navigator', {
    serviceWorker: { getRegistration: vi.fn().mockResolvedValue({ pushManager: manager }) },
  });
  return { manager, created };
}

beforeEach(() => {
  publicKey = 'BA';
  localStorage.removeItem('ase-push-device');
  registered.mockClear();
  removed.mockClear();
  vi.stubGlobal('crypto', webcrypto);
  server.use(
    http.get('/api/me/notifications/push', () =>
      HttpResponse.json({
        available: true,
        public_key: publicKey,
        devices: [{ id: 'replaced', endpoint_hash: 'old-hash', created_at: 'now' }],
      }),
    ),
    http.post('/api/me/notifications/push', async ({ request }) => {
      registered(await request.json());
      return HttpResponse.json({ id: 'renewed', endpoint_hash: 'new-hash', created_at: 'now' });
    }),
    http.delete('/api/me/notifications/push/:id', ({ params }) => {
      removed(params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('push subscription renewal', () => {
  it('registers a subscription the worker replaced and retires the old device', async () => {
    const current = subscriptionFor('https://push.example/replacement');
    browser(current);
    rememberPush('user-a', 'old-hash');
    await expect(renewPush('user-a')).resolves.toBe(true);
    expect(registered).toHaveBeenCalledWith({
      endpoint: current.endpoint,
      p256dh: 'key',
      auth: 'secret',
    });
    expect(removed).toHaveBeenCalledWith('replaced');
    expect(pushRecord()).toEqual({ owner: 'user-a', hash: 'new-hash' });
  });

  it('subscribes again with the server key when the browser dropped the subscription', async () => {
    const { manager, created } = browser(null);
    rememberPush('user-a', 'gone-hash');
    await expect(renewPush('user-a')).resolves.toBe(true);
    expect(manager.subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: expect.any(Uint8Array),
    });
    expect(registered).toHaveBeenCalledWith(
      expect.objectContaining({ endpoint: created.endpoint }),
    );
    expect(removed).not.toHaveBeenCalled();
  });

  it('does nothing while the registered subscription is unchanged', async () => {
    const current = subscriptionFor('https://push.example/same');
    browser(current);
    rememberPush('user-a', await hashOf(current));
    await expect(renewPush('user-a')).resolves.toBe(false);
    expect(registered).not.toHaveBeenCalled();
  });

  it.each([
    ['another account opted this browser in', 'user-b', 'granted'],
    ['notification permission was withdrawn', 'user-a', 'denied'],
  ])('never claims the browser when %s', async (_case, owner, permission) => {
    browser(null, permission);
    rememberPush(owner, 'old-hash');
    await expect(renewPush('user-a')).resolves.toBe(false);
    expect(registered).not.toHaveBeenCalled();
  });

  it('does nothing without a record, a worker registration or a server key', async () => {
    browser(null);
    await expect(renewPush('user-a')).resolves.toBe(false);
    rememberPush('user-a', 'old-hash');
    publicKey = null;
    await expect(renewPush('user-a')).resolves.toBe(false);
    vi.stubGlobal('navigator', {
      serviceWorker: { getRegistration: vi.fn().mockResolvedValue(undefined) },
    });
    await expect(renewPush('user-a')).resolves.toBe(false);
    expect(registered).not.toHaveBeenCalled();
  });

  it('stops if the account signs out while the browser subscribes', async () => {
    const { manager, created } = browser(null);
    rememberPush('user-a', 'old-hash');
    manager.subscribe.mockImplementation(async () => {
      await clearBrowserPush();
      return created;
    });
    await expect(renewPush('user-a')).resolves.toBe(false);
    expect(registered).not.toHaveBeenCalled();
    expect(pushRecord()).toBeNull();
  });

  it('ignores a malformed record', async () => {
    browser(null);
    localStorage.setItem('ase-push-device', '{"owner":1}');
    expect(pushRecord()).toBeNull();
    localStorage.setItem('ase-push-device', 'not json');
    expect(pushRecord()).toBeNull();
    await expect(renewPush('user-a')).resolves.toBe(false);
  });
});
