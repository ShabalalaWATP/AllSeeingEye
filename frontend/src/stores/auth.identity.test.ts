import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { pushRecord, rememberPush } from '@/lib/browserPush';
import * as authApi from '@/lib/api/auth';
import { clearCookies, setCsrfCookie } from '@/test/env';
import { adminUser, CSRF_VALUE, plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

const original = tokenFor(plainUser);
const rotated = tokenFor(plainUser, { revision: 'rotated' });
const replacement = tokenFor(adminUser);

function signIn() {
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);
  rememberPush(plainUser.id, 'endpoint');
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'locks');
});

it.each(['success', '401', '403'])(
  'discards a late refresh %s after a replacement login',
  async (result) => {
    signIn();
    const gate = deferred();
    let sent = false;
    server.use(
      http.post('/api/auth/refresh', async () => {
        sent = true;
        await gate.promise;
        return result === 'success'
          ? HttpResponse.json(rotated)
          : apiError(Number(result), 'invalid_refresh', 'Expired.');
      }),
    );
    const pending = useAuthStore.getState().refresh();
    await vi.waitFor(() => expect(sent).toBe(true));
    useAuthStore.getState().setSession(replacement);
    gate.resolve();
    await expect(pending).resolves.toBeNull();
    expect(useAuthStore.getState()).toMatchObject({
      user: adminUser,
      accessToken: replacement.access_token,
    });
    expect(pushRecord()).toEqual({ owner: plainUser.id, hash: 'endpoint' });
  },
);

it('does not resurrect a cleared session after refresh succeeds', async () => {
  signIn();
  const gate = deferred();
  let sent = false;
  server.use(
    http.post('/api/auth/refresh', async () => {
      sent = true;
      await gate.promise;
      return HttpResponse.json(rotated);
    }),
  );
  const pending = useAuthStore.getState().refresh();
  await vi.waitFor(() => expect(sent).toBe(true));
  useAuthStore.getState().clearSession();
  gate.resolve();
  await expect(pending).resolves.toBeNull();
  expect(useAuthStore.getState().status).toBe('anonymous');
});

it('detaches previous refresh work and keeps the replacement pending refresh deduplicated', async () => {
  signIn();
  const gates = [deferred(), deferred()];
  let calls = 0;
  server.use(
    http.post('/api/auth/refresh', async () => {
      const index = calls++;
      await gates[index]!.promise;
      return HttpResponse.json(index === 0 ? rotated : replacement);
    }),
  );
  const first = useAuthStore.getState().refresh();
  await vi.waitFor(() => expect(calls).toBe(1));
  useAuthStore.getState().setSession(replacement);
  const second = useAuthStore.getState().refresh();
  // Release the old request even if the vulnerable implementation reuses its promise.
  gates[0]!.resolve();
  await first;
  await vi.waitFor(() => expect(calls).toBe(2));
  expect(useAuthStore.getState().pendingRefresh).toBe(second);
  expect(useAuthStore.getState().refresh()).toBe(second);
  gates[1]!.resolve();
  await expect(second).resolves.toBe(replacement.access_token);
});

it('does not send a queued refresh after the local login changes', async () => {
  signIn();
  const gate = deferred();
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: {
      request: async (_name: string, work: () => Promise<unknown>) => {
        await gate.promise;
        return work();
      },
    },
  });
  const request = vi.fn(() => HttpResponse.json(rotated));
  server.use(http.post('/api/auth/refresh', request));
  const pending = useAuthStore.getState().refresh();
  useAuthStore.getState().setSession(replacement);
  gate.resolve();
  await expect(pending).resolves.toBeNull();
  expect(request).not.toHaveBeenCalled();
});

it.each([
  ['another account', replacement],
  ['the same account with another family', tokenFor(plainUser, { familyId: 'new-login' })],
  ['a mismatched response user', { ...rotated, user: adminUser }],
  ['an opaque access token', { ...rotated, access_token: 'unrecognised' }],
])('rejects a refresh response for %s without adopting it', async (_label, response) => {
  signIn();
  server.use(
    http.post('/api/auth/refresh', () => {
      // A different tab has changed the browser cookie without changing this tab's store.
      setCsrfCookie('another-tab-cookie');
      return HttpResponse.json(response);
    }),
  );
  await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
  expect(useAuthStore.getState()).toMatchObject({
    user: plainUser,
    accessToken: original.access_token,
  });
  expect(pushRecord()).toEqual({ owner: plainUser.id, hash: 'endpoint' });
});

it.each([401, 403])(
  'does not clear shared push after cookies change during a rejected %s refresh',
  async (status) => {
    signIn();
    server.use(
      http.post('/api/auth/refresh', () => {
        setCsrfCookie('another-tab-cookie');
        return apiError(status, 'invalid_refresh', 'Expired.');
      }),
    );
    await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
    expect(useAuthStore.getState().accessToken).toBe(original.access_token);
    expect(pushRecord()).toEqual({ owner: plainUser.id, hash: 'endpoint' });
  },
);

it('deduplicates legitimate same-family rotation despite a cross-tab cookie change', async () => {
  signIn();
  const handler = vi.fn(() => {
    setCsrfCookie('rotated-cookie');
    return HttpResponse.json(rotated);
  });
  server.use(http.post('/api/auth/refresh', handler));
  const first = useAuthStore.getState().refresh();
  expect(useAuthStore.getState().refresh()).toBe(first);
  await expect(first).resolves.toBe(rotated.access_token);
  expect(useAuthStore.getState().accessToken).toBe(rotated.access_token);
  expect(handler).toHaveBeenCalledTimes(1);
});

it('invalidates refresh at logout start and keeps replacement login cookies after logout completes', async () => {
  signIn();
  const gate = deferred();
  let sent = false;
  let loginSent = false;
  server.use(
    http.post('/api/auth/logout', async () => {
      sent = true;
      await gate.promise;
      clearCookies();
      return new HttpResponse(null, { status: 204 });
    }),
    http.post('/api/auth/login', () => {
      loginSent = true;
      setCsrfCookie('replacement-login-cookie');
      return HttpResponse.json(replacement);
    }),
  );
  const pending = useAuthStore.getState().logout();
  await vi.waitFor(() => expect(sent).toBe(true));
  expect(useAuthStore.getState().status).toBe('anonymous');
  const sendLogin = vi.spyOn(authApi, 'login');
  const login = useAuthStore.getState().login(adminUser.email, 'password');
  const sentBeforeLogout = sendLogin.mock.calls.length;
  // If the bug permits the login, finish it before delivering the logout response.
  if (sentBeforeLogout > 0) await login;
  gate.resolve();
  await Promise.all([pending, login]);
  expect(sentBeforeLogout).toBe(0);
  expect(loginSent).toBe(true);
  expect(useAuthStore.getState().accessToken).toBe(replacement.access_token);
  expect(document.cookie).toContain('replacement-login-cookie');
});

it.each([
  ['unrecognised token', 'opaque', plainUser],
  ['mismatched current account', original.access_token, adminUser],
])('refuses to refresh an authenticated state with %s', async (_label, accessToken, user) => {
  useAuthStore.setState({ status: 'authenticated', user, accessToken });
  const request = vi.fn(() => HttpResponse.json(replacement));
  server.use(http.post('/api/auth/refresh', request));
  await expect(useAuthStore.getState().refresh()).resolves.toBeNull();
  expect(request).not.toHaveBeenCalled();
});

it('does not adopt a login response after another login establishes its session', async () => {
  const gate = deferred();
  let sent = false;
  server.use(
    http.post('/api/auth/login', async () => {
      sent = true;
      await gate.promise;
      return HttpResponse.json(original);
    }),
  );
  const pending = useAuthStore
    .getState()
    .login(plainUser.email, 'password')
    .catch((error: unknown) => error);
  await vi.waitFor(() => expect(sent).toBe(true));
  useAuthStore.getState().setSession(replacement);
  gate.resolve();
  await expect(pending).resolves.toMatchObject({ code: 'session_changed' });
  expect(useAuthStore.getState().accessToken).toBe(replacement.access_token);
});

it('deduplicates logout and cancels a waiting login when its generation is cleared', async () => {
  signIn();
  const gate = deferred();
  let sent = 0;
  const sendLogin = vi.spyOn(authApi, 'login');
  server.use(
    http.post('/api/auth/logout', async () => {
      sent++;
      await gate.promise;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const logout = useAuthStore.getState().logout();
  expect(useAuthStore.getState().logout()).toBe(logout);
  const login = useAuthStore
    .getState()
    .login(adminUser.email, 'password')
    .catch((error: unknown) => error);
  await vi.waitFor(() => expect(sent).toBe(1));
  useAuthStore.getState().clearSession();
  gate.resolve();
  await logout;
  await expect(login).resolves.toMatchObject({ code: 'session_changed' });
  expect(sendLogin).not.toHaveBeenCalled();
  expect(useAuthStore.getState().pendingLogout).toBeNull();
});

it('keeps MFA pending without establishing an authenticated session', async () => {
  server.use(
    http.post('/api/auth/login', () =>
      HttpResponse.json({
        mfa_required: true,
        challenge_token: 'challenge',
        methods: ['authenticator'],
        expires_at: '2026-10-09T23:59:59Z',
        enrollment_required: false,
        email_sent: false,
        authenticator_email_proof: false,
      }),
    ),
  );
  await expect(useAuthStore.getState().login(plainUser.email, 'password')).resolves.toMatchObject({
    mfa_required: true,
  });
  expect(useAuthStore.getState().accessToken).toBeNull();
});
