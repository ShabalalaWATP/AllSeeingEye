import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { setCsrfCookie } from '@/test/env';
import { CSRF_VALUE, plainUser, sessionActivity, tokenFor, USER_PASSWORD } from '@/test/fixtures';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

const NOW = Date.parse('2026-10-09T12:00:00Z');
function signIn() {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(tokenFor(plainUser));
}
function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
afterEach(() => vi.useRealTimers());

it.each([200, 204])(
  'does not apply a late conditional%s result to a replacement login',
  async (status) => {
    signIn();
    const gate = deferred();
    let sent = false;
    server.use(
      http.post('/api/auth/logout', async () => {
        sent = true;
        await gate.promise;
        return status === 200
          ? HttpResponse.json(sessionActivity(NOW + 60_000))
          : new HttpResponse(null, { status: 204 });
      }),
    );
    const pending = useAuthStore.getState().expireIdleSession();
    await vi.waitFor(() => expect(sent).toBe(true));
    const replacement = tokenFor(plainUser, { familyId: 'replacement-login' });
    useAuthStore.getState().setSession(replacement);
    gate.resolve();
    await pending;
    expect(useAuthStore.getState().accessToken).toBe(replacement.access_token);
    expect(useAuthStore.getState().activity?.data).toEqual(replacement.activity);
    expect(useAuthStore.getState().idleExpiryConfirmed).toBe(false);
  },
);

it('allows a new login while a read-only conditional check is pending', async () => {
  signIn();
  const gate = deferred();
  let checking = false;
  const login = vi.fn(() => HttpResponse.json(tokenFor(plainUser, { familyId: 'new-login' })));
  server.use(
    http.post('/api/auth/logout', async () => {
      checking = true;
      await gate.promise;
      return new HttpResponse(null, { status: 204 });
    }),
    http.post('/api/auth/login', login),
  );
  const check = useAuthStore.getState().expireIdleSession();
  await vi.waitFor(() => expect(checking).toBe(true));
  const signingIn = useAuthStore.getState().login(plainUser.email, USER_PASSWORD);
  try {
    await vi.waitFor(() => expect(login).toHaveBeenCalledOnce());
  } finally {
    gate.resolve();
    await Promise.all([check, signingIn]);
  }
  expect(login).toHaveBeenCalledOnce();
  expect(useAuthStore.getState().status).toBe('authenticated');
});

it('allows explicit logout while a read-only conditional check is pending', async () => {
  signIn();
  const gate = deferred();
  const requests: (string | null)[] = [];
  server.use(
    http.post('/api/auth/logout', async ({ request }) => {
      requests.push(request.headers.get('X-ASE-Idle-Expired'));
      if (requests.length === 1) {
        await gate.promise;
        return HttpResponse.json(sessionActivity());
      }
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const check = useAuthStore.getState().expireIdleSession();
  await vi.waitFor(() => expect(requests).toEqual(['1']));
  const logout = useAuthStore.getState().logout();
  expect(useAuthStore.getState().status).toBe('anonymous');
  try {
    await vi.waitFor(() => expect(requests).toEqual(['1', null]));
  } finally {
    gate.resolve();
    await Promise.all([check, logout]);
  }
  expect(requests).toEqual(['1', null]);
});

it('aborts a stalled conditional check after ten seconds without extending the deadline', async () => {
  signIn();
  vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] });
  const original = useAuthStore.getState().activity;
  let rejectRequest!: (reason: unknown) => void;
  let signal: AbortSignal | null | undefined;
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) => {
    signal = init?.signal;
    return new Promise<Response>((_resolve, reject) => {
      rejectRequest = reject;
      signal?.addEventListener(
        'abort',
        () => reject(new DOMException('The operation was aborted.', 'AbortError')),
        { once: true },
      );
    });
  });
  const check = useAuthStore.getState().expireIdleSession();
  expect(useAuthStore.getState().expireIdleSession()).toBe(check);
  try {
    await vi.advanceTimersByTimeAsync(10_000);
    expect(signal?.aborted).toBe(true);
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      pendingIdleCheck: null,
      idleCheckRetryAt: NOW + 70_000,
      idleExpiryConfirmed: false,
    });
    expect(useAuthStore.getState().activityError).toBeTruthy();
    expect(useAuthStore.getState().activity).toBe(original);
    await useAuthStore.getState().expireIdleSession();
    expect(fetch).toHaveBeenCalledOnce();
  } finally {
    rejectRequest(new Error('test cleanup'));
    await check;
    fetch.mockRestore();
  }
});

it('keeps the deadline unchanged after a network failure and retries at most once a minute', async () => {
  signIn();
  const original = useAuthStore.getState().activity;
  const request = vi.fn(() => HttpResponse.error());
  server.use(http.post('/api/auth/logout', request));
  await useAuthStore.getState().expireIdleSession();
  expect(useAuthStore.getState().activity).toBe(original);
  expect(useAuthStore.getState()).toMatchObject({
    status: 'authenticated',
    idleExpiryConfirmed: false,
  });
  vi.setSystemTime(NOW + 59_999);
  await useAuthStore.getState().expireIdleSession();
  expect(request).toHaveBeenCalledOnce();
  vi.setSystemTime(NOW + 60_000);
  await useAuthStore.getState().expireIdleSession();
  expect(request).toHaveBeenCalledTimes(2);
});
