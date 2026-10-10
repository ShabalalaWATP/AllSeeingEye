import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { pushRecord, rememberPush } from '@/lib/browserPush';
import { CSRF_COOKIE, readCookie } from '@/lib/csrf';
import { setCsrfCookie } from '@/test/env';
import { adminUser, CSRF_VALUE } from '@/test/fixtures';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

function holdRefreshLock() {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const request = vi.fn(async (_name: string, work: () => Promise<unknown>) => {
    await gate;
    return work();
  });
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request } });
  return { request, release };
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'locks');
});

it('logs out a cookie-only session after its unchanged cookie obtains the refresh lock', async () => {
  // Before bootstrap there is a browser session, but no in-memory family identity.
  setCsrfCookie(CSRF_VALUE);
  const lock = holdRefreshLock();
  const requests: Request[] = [];
  server.use(
    http.post('/api/auth/logout', ({ request }) => {
      requests.push(request);
      return new HttpResponse(null, { status: 204 });
    }),
  );

  const pending = useAuthStore.getState().logout();
  await vi.waitFor(() =>
    expect(lock.request).toHaveBeenCalledWith('ase-refresh', expect.any(Function)),
  );
  expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', pendingLogout: pending });
  expect(requests).toHaveLength(0);
  lock.release();
  await pending;

  expect(requests).toHaveLength(1);
  expect(requests[0]!.headers.get('X-CSRF-Token')).toBe(CSRF_VALUE);
  expect(requests[0]!.headers.get('X-ASE-Session-Family')).toBeNull();
  expect(requests[0]!.headers.get('Authorization')).toBeNull();
  expect(useAuthStore.getState().pendingLogout).toBeNull();
});

it('skips cookie-only logout when another tab replaces the cookie while the lock is held', async () => {
  setCsrfCookie(CSRF_VALUE);
  const lock = holdRefreshLock();
  const request = vi.fn(() => new HttpResponse(null, { status: 204 }));
  server.use(http.post('/api/auth/logout', request));

  const pending = useAuthStore.getState().logout();
  await vi.waitFor(() => expect(lock.request).toHaveBeenCalledTimes(1));
  expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', pendingLogout: pending });
  expect(request).not.toHaveBeenCalled();

  // A different tab owns the shared cookie and push subscription before this request runs.
  setCsrfCookie('replacement-cookie');
  rememberPush(adminUser.id, 'replacement-endpoint');
  lock.release();
  await pending;

  expect(request).not.toHaveBeenCalled();
  expect(readCookie(CSRF_COOKIE)).toBe('replacement-cookie');
  expect(pushRecord()).toEqual({ owner: adminUser.id, hash: 'replacement-endpoint' });
  expect(useAuthStore.getState()).toMatchObject({
    status: 'anonymous',
    user: null,
    accessToken: null,
    pendingLogout: null,
  });
});
