import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setCsrfCookie } from '@/test/env';
import { ADMIN_TOKEN, CSRF_VALUE, adminUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

const unsubscribe = vi.fn(() => Promise.resolve(true));

/** A push-capable browser with one subscription, so a cleared session unsubscribes it. */
function pushBrowser() {
  const registration = { pushManager: { getSubscription: () => Promise.resolve({ unsubscribe }) } };
  vi.stubGlobal('isSecureContext', true);
  vi.stubGlobal('PushManager', vi.fn());
  vi.stubGlobal('Notification', {});
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { getRegistration: () => Promise.resolve(registration) },
  });
}

function signedIn() {
  pushBrowser();
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(tokenFor(adminUser));
}

function installLocks(request: (name: string, work: () => Promise<unknown>) => Promise<unknown>) {
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request } });
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'locks');
  Reflect.deleteProperty(navigator, 'serviceWorker');
  vi.unstubAllGlobals();
  unsubscribe.mockClear();
});

describe('refresh failure handling', () => {
  it.each([401, 403])('ends the session and browser push on a %i rejection', async (status) => {
    signedIn();
    server.use(http.post('/api/auth/refresh', () => apiError(status, 'invalid_refresh', 'No.')));
    await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
    expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', accessToken: null });
    await vi.waitFor(() => expect(unsubscribe).toHaveBeenCalledTimes(1));
  });

  it.each([
    ['a server error', () => apiError(503, 'unavailable', 'Try later.')],
    ['a network failure', () => HttpResponse.error()],
  ])('keeps the session after %s and lets a later refresh succeed', async (_label, failure) => {
    signedIn();
    let fail = true;
    server.use(
      http.post('/api/auth/refresh', () =>
        fail ? failure() : HttpResponse.json({ ...tokenFor(adminUser), access_token: 'later' }),
      ),
    );
    await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      accessToken: ADMIN_TOKEN,
      pendingRefresh: null,
    });
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(unsubscribe).not.toHaveBeenCalled();
    fail = false;
    await expect(useAuthStore.getState().refresh()).resolves.toBe('later');
  });

  it('settles an unavailable bootstrap as signed out without touching browser push', async () => {
    pushBrowser();
    setCsrfCookie(CSRF_VALUE);
    server.use(http.post('/api/auth/refresh', () => apiError(502, 'bad_gateway', 'Down.')));
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', accessToken: null });
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(unsubscribe).not.toHaveBeenCalled();
  });
});

describe('cross-tab refresh serialisation', () => {
  it('sends the refresh only once the shared lock is granted', async () => {
    signedIn();
    let sent = 0;
    server.use(
      http.post('/api/auth/refresh', () => {
        sent += 1;
        return HttpResponse.json({ ...tokenFor(adminUser), access_token: 'rotated' });
      }),
    );
    let grant!: () => void;
    const granted = new Promise<void>((resolve) => {
      grant = resolve;
    });
    const request = vi.fn(async (_name: string, work: () => Promise<unknown>) => {
      await granted;
      return work();
    });
    installLocks(request);
    const attempt = useAuthStore.getState().refresh();
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(request).toHaveBeenCalledWith('ase-refresh', expect.any(Function));
    expect(sent).toBe(0);
    grant();
    await expect(attempt).resolves.toBe('rotated');
    expect(sent).toBe(1);
  });

  it('keeps the session when the lock itself cannot be taken', async () => {
    signedIn();
    installLocks(() => Promise.reject(new DOMException('Denied', 'SecurityError')));
    await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
    expect(useAuthStore.getState().status).toBe('authenticated');
  });
});
