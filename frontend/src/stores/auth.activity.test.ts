import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { apiSend } from '@/lib/api/client';
import { sessionIdentity } from '@/lib/sessionIdentity';
import { pushRecord, rememberPush } from '@/lib/browserPush';
import { setCsrfCookie } from '@/test/env';
import { CSRF_VALUE, plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

const NOW = Date.parse('2026-10-09T12:00:00Z');
function activity(minutes = 180, last = NOW - 120_000) {
  return {
    server_now: new Date(NOW).toISOString(),
    last_activity_at: new Date(last).toISOString(),
    idle_expires_at: new Date(last + minutes * 60_000).toISOString(),
    idle_minutes: minutes,
  };
}

function signIn() {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  setCsrfCookie(CSRF_VALUE);
  const token = { ...tokenFor(plainUser), activity: activity() };
  useAuthStore.getState().setSession(token);
  return token;
}

afterEach(() => vi.useRealTimers());

it('checks server activity before a stale tab can sign out a family another tab kept alive', async () => {
  signIn();
  const later = NOW + 180 * 60_000;
  vi.setSystemTime(later);
  const confirmed = {
    server_now: new Date(later).toISOString(),
    last_activity_at: new Date(later - 30_000).toISOString(),
    idle_expires_at: new Date(later + 180 * 60_000 - 30_000).toISOString(),
    idle_minutes: 180,
  };
  let conditional: string | null = null;
  server.use(
    http.post('/api/auth/logout', ({ request }) => {
      conditional = request.headers.get('X-ASE-Idle-Expired');
      return HttpResponse.json(confirmed);
    }),
  );
  await useAuthStore.getState().expireIdleSession();
  expect(useAuthStore.getState().status).toBe('authenticated');
  expect(useAuthStore.getState().activity?.data).toEqual(confirmed);
  expect(conditional).toBe('1');
});

it('retains confirmed activity across passive refresh without sending an activity header', async () => {
  signIn();
  const refreshed = { ...tokenFor(plainUser, { revision: 'rotated' }), activity: activity() };
  server.use(
    http.post('/api/auth/refresh', ({ request }) => {
      expect(request.headers.has('x-ase-activity')).toBe(false);
      return HttpResponse.json(refreshed);
    }),
  );
  await useAuthStore.getState().refresh();
  expect(useAuthStore.getState().activity?.data).toEqual(refreshed.activity);
});

it('ends an explicitly idle session before automatic refresh can revive it', async () => {
  signIn();
  const refresh = vi.fn(() => HttpResponse.json(tokenFor(plainUser)));
  server.use(
    http.get('/api/idle-test', () => apiError(401, 'session_idle_expired', 'Idle session.')),
    http.post('/api/auth/refresh', refresh),
  );
  await expect(apiSend('/api/idle-test')).rejects.toMatchObject({ code: 'session_idle_expired' });
  await useAuthStore.getState().pendingIdleCheck;
  expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', idleExpiredMinutes: 180 });
  expect(refresh).not.toHaveBeenCalled();
  await useAuthStore.getState().pendingLogout;
});

it('binds a heartbeat to the original bearer and CSRF cookie, then throttles for a minute', async () => {
  const original = signIn();
  const requests = vi.fn(({ request }: { request: Request }) => {
    expect(request.headers.get('Authorization')).toBe(`Bearer ${original.access_token}`);
    expect(request.headers.get('X-CSRF-Token')).toBe(CSRF_VALUE);
    return HttpResponse.json(activity(180, NOW));
  });
  server.use(http.post('/api/auth/activity', requests));
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(true);
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  expect(requests).toHaveBeenCalledTimes(1);
});

it.each(['success', '401', '403'])(
  'discards a late heartbeat %s after the login family changes',
  async (outcome) => {
    signIn();
    let resolve!: () => void;
    const gate = new Promise<void>((done) => {
      resolve = done;
    });
    let sent = false;
    server.use(
      http.post('/api/auth/activity', async () => {
        sent = true;
        await gate;
        return outcome === 'success'
          ? HttpResponse.json(activity(180, NOW))
          : apiError(Number(outcome), 'session_idle_expired', 'Idle session.');
      }),
    );
    const pending = useAuthStore.getState().reportActivity();
    await vi.waitFor(() => expect(sent).toBe(true));
    const replacement = {
      ...tokenFor(plainUser, { familyId: 'replacement' }),
      activity: activity(15),
    };
    useAuthStore.getState().setSession(replacement);
    resolve();
    await expect(pending).resolves.toBe(false);
    expect(useAuthStore.getState().activity?.data).toEqual(replacement.activity);
  },
);

it("binds idle logout to the old family and preserves another tab's browser push record", async () => {
  const original = signIn();
  rememberPush(plainUser.id, 'another-tab-endpoint');
  setCsrfCookie('another-tab-cookie');
  const logout = vi.fn(({ request }: { request: Request }) => {
    expect(request.headers.get('X-ASE-Session-Family')).toBe(
      sessionIdentity(original.access_token)?.familyId,
    );
    return new HttpResponse(null, { status: 204 });
  });
  server.use(http.post('/api/auth/logout', logout));
  const pending = useAuthStore.getState().expireIdleSession();
  await pending;
  expect(useAuthStore.getState().accessToken).toBeNull();
  expect(pushRecord()).toEqual({ owner: plainUser.id, hash: 'another-tab-endpoint' });
  expect(logout).toHaveBeenCalledOnce();
});

it('keeps the confirmed deadline after a429 and obeys Retry-After without automatic retries', async () => {
  signIn();
  const original = useAuthStore.getState().activity;
  const heartbeat = vi.fn(() =>
    HttpResponse.json(
      { error: { code: 'rate_limited', message: 'Wait.' } },
      { status: 429, headers: { 'Retry-After': '90' } },
    ),
  );
  server.use(http.post('/api/auth/activity', heartbeat));
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  expect(useAuthStore.getState().activity).toBe(original);
  vi.setSystemTime(NOW + 89_999);
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  expect(heartbeat).toHaveBeenCalledOnce();
  vi.setSystemTime(NOW + 90_000);
  await useAuthStore.getState().reportActivity();
  expect(heartbeat).toHaveBeenCalledTimes(2);
});

it('can refresh an expired access token and send the heartbeat only within its original family', async () => {
  signIn();
  const rotated = {
    ...tokenFor(plainUser, { revision: 'heartbeat-refresh' }),
    activity: activity(),
  };
  const sent: (string | null)[] = [];
  server.use(
    http.post('/api/auth/activity', ({ request }) => {
      sent.push(request.headers.get('Authorization'));
      return sent.length === 1
        ? apiError(401, 'unauthenticated', 'Expired access token.')
        : HttpResponse.json(activity(180, NOW));
    }),
    http.post('/api/auth/refresh', ({ request }) => {
      expect(request.headers.has('x-ase-activity')).toBe(false);
      return HttpResponse.json(rotated);
    }),
  );
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(true);
  expect(sent).toHaveLength(2);
  expect(sent[1]).toBe(`Bearer ${rotated.access_token}`);
});

it('does not retry a heartbeat using a different family returned by the shared refresh cookie', async () => {
  const original = signIn();
  const heartbeat = vi.fn(() => apiError(401, 'unauthenticated', 'Expired access token.'));
  server.use(
    http.post('/api/auth/activity', heartbeat),
    http.post('/api/auth/refresh', () => {
      setCsrfCookie('replacement-cookie');
      return HttpResponse.json(tokenFor(plainUser, { familyId: 'new-login' }));
    }),
  );
  await expect(useAuthStore.getState().reportActivity()).resolves.toBe(false);
  expect(heartbeat).toHaveBeenCalledOnce();
  expect(useAuthStore.getState().accessToken).toBe(original.access_token);
});

it('reports the configured duration when bootstrap discovers an idle family', async () => {
  setCsrfCookie(CSRF_VALUE);
  server.use(
    http.post('/api/auth/refresh', () =>
      HttpResponse.json(
        {
          error: {
            code: 'session_idle_expired',
            message: 'Idle session.',
            fields: { idle_minutes: '15' },
          },
        },
        { status: 401 },
      ),
    ),
  );
  await useAuthStore.getState().bootstrap();
  expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', idleExpiredMinutes: 15 });
});
