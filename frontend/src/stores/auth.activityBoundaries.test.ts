import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { setCsrfCookie } from '@/test/env';
import { CSRF_VALUE, plainUser, sessionActivity, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

const NOW = Date.parse('2026-10-09T12:00:00Z');
function signIn() {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(tokenFor(plainUser));
  vi.setSystemTime(NOW + 61_000);
}
afterEach(() => vi.useRealTimers());

it('does not contact activity endpoints without a recognised authenticated owner', async () => {
  useAuthStore.getState().clearSession();
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  await expect(useAuthStore.getState().expireIdleSession()).resolves.toBeUndefined();
  signIn();
  useAuthStore.setState({ accessToken: 'unrecognised' });
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  await expect(useAuthStore.getState().expireIdleSession()).resolves.toBeUndefined();
});

it('deduplicates simultaneous genuine activity requests', async () => {
  signIn();
  let resolve!: () => void;
  const gate = new Promise<void>((done) => {
    resolve = done;
  });
  const send = vi.fn(async () => {
    await gate;
    return HttpResponse.json(sessionActivity(Date.now()));
  });
  server.use(http.post('/api/auth/activity', send));
  const first = useAuthStore.getState().reportActivity();
  expect(useAuthStore.getState().reportActivity()).toBe(first);
  resolve();
  await first;
  expect(send).toHaveBeenCalledOnce();
});

it.each([true, false])(
  'verifies a stale deadline before Stay attempts a heartbeat, live=%s',
  async (live) => {
    signIn();
    vi.setSystemTime(NOW + 181 * 60_000);
    const confirmed = sessionActivity(Date.now());
    const earlier = {
      ...confirmed,
      last_activity_at: new Date(Date.now() - 120_000).toISOString(),
    };
    const heartbeat = vi.fn(() => HttpResponse.json(confirmed));
    server.use(
      http.post('/api/auth/logout', () =>
        live ? HttpResponse.json(earlier) : new HttpResponse(null, { status: 204 }),
      ),
      http.post('/api/auth/activity', heartbeat),
    );
    await expect(useAuthStore.getState().reportActivity()).resolves.toBe(live);
    expect(heartbeat).toHaveBeenCalledTimes(live ? 1 : 0);
    expect(useAuthStore.getState().status).toBe(live ? 'authenticated' : 'anonymous');
  },
);

it('confirms an explicit heartbeat idle rejection and keeps the current configured duration', async () => {
  signIn();
  server.use(
    http.post('/api/auth/activity', () =>
      HttpResponse.json(
        {
          error: {
            code: 'session_idle_expired',
            message: 'Expired.',
            fields: { idle_minutes: '15' },
          },
        },
        { status: 401 },
      ),
    ),
  );
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  await useAuthStore.getState().pendingIdleCheck;
  expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', idleExpiredMinutes: 15 });
});

it.each(['network', 'rate_limit'])(
  'does not extend activity after a %s failure without retry metadata',
  async (kind) => {
    signIn();
    const original = useAuthStore.getState().activity;
    server.use(
      http.post('/api/auth/activity', () =>
        kind === 'network' ? HttpResponse.error() : apiError(429, 'rate_limited', 'Wait.'),
      ),
    );
    await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
    expect(useAuthStore.getState().activity).toBe(original);
    expect(useAuthStore.getState().activityRetryAt).toBe(Date.now() + 60_000);
  },
);
