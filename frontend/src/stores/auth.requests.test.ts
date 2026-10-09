import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiBlob, apiCall, apiFile, apiSend, apiText } from '@/lib/api/client';
import { pushRecord, rememberPush } from '@/lib/browserPush';
import { setCsrfCookie } from '@/test/env';
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

const expired = () => apiError(401, 'unauthenticated', 'Expired.');
const original = tokenFor(plainUser);
const rotated = tokenFor(plainUser, { revision: 'rotated' });

it.each(['other account', 'same account new family', 'logout and login'])(
  'does not replay a delayed mutation after %s',
  async (transition) => {
    setCsrfCookie(CSRF_VALUE);
    useAuthStore.getState().setSession(original);
    const gate = deferred();
    const seen: (string | null)[] = [];
    const replacement =
      transition === 'other account'
        ? tokenFor(adminUser)
        : tokenFor(plainUser, { familyId: 'new-login' });
    const refresh = vi.fn(() => HttpResponse.json(replacement));
    server.use(
      http.post('/api/private-mutation', async ({ request }) => {
        seen.push(request.headers.get('Authorization'));
        if (seen.length === 1) {
          await gate.promise;
          return expired();
        }
        return new HttpResponse(null, { status: 204 });
      }),
      http.post('/api/auth/refresh', refresh),
    );
    const pending = apiSend('/api/private-mutation', {
      method: 'POST',
      body: { private: 'draft' },
    }).catch((error: unknown) => error);
    await vi.waitFor(() => expect(seen).toHaveLength(1));
    if (transition === 'logout and login') useAuthStore.getState().clearSession();
    useAuthStore.getState().setSession(replacement);
    gate.resolve();
    await expect(pending).resolves.toMatchObject({ code: 'session_changed' });
    expect(refresh).not.toHaveBeenCalled();
    expect(seen).toEqual([`Bearer ${original.access_token}`]);
  },
);

it('does not clear a replacement login after a delayed second 401', async () => {
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);
  const gate = deferred();
  let sent = 0;
  server.use(
    http.post('/api/private-mutation', async () => {
      if (++sent === 2) await gate.promise;
      return expired();
    }),
    http.post('/api/auth/refresh', () => HttpResponse.json(rotated)),
  );
  const pending = apiSend('/api/private-mutation', { method: 'POST' }).catch(
    (error: unknown) => error,
  );
  await vi.waitFor(() => expect(sent).toBe(2));
  const replacement = tokenFor(adminUser);
  useAuthStore.getState().setSession(replacement);
  gate.resolve();
  await expect(pending).resolves.toMatchObject({ code: 'session_changed' });
  expect(useAuthStore.getState().accessToken).toBe(replacement.access_token);
});

it('keeps shared browser push when another tab changes cookies during a retried request', async () => {
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);
  const gate = deferred();
  let sent = 0;
  server.use(
    http.post('/api/private-mutation', async () => {
      if (++sent === 2) await gate.promise;
      return expired();
    }),
    http.post('/api/auth/refresh', () => HttpResponse.json(rotated)),
  );
  const pending = apiSend('/api/private-mutation', { method: 'POST' }).catch(
    (error: unknown) => error,
  );
  await vi.waitFor(() => expect(sent).toBe(2));
  setCsrfCookie('replacement-login-cookie');
  rememberPush(adminUser.id, 'replacement-endpoint');
  gate.resolve();
  await expect(pending).resolves.toMatchObject({ status: 401 });
  expect(pushRecord()).toEqual({ owner: adminUser.id, hash: 'replacement-endpoint' });
  expect(useAuthStore.getState().accessToken).toBe(rotated.access_token);
});

it('allows delayed 401s from the same login after another request rotates the bearer', async () => {
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);
  const gate = deferred();
  let firstSent = false;
  server.use(
    http.get('/api/concurrent', async ({ request }) => {
      if (request.headers.get('Authorization') === `Bearer ${rotated.access_token}`) {
        return new HttpResponse(null, { status: 204 });
      }
      firstSent = true;
      await gate.promise;
      return expired();
    }),
    http.post('/api/auth/refresh', () => HttpResponse.json(rotated)),
  );
  const pending = apiSend('/api/concurrent');
  await vi.waitFor(() => expect(firstSent).toBe(true));
  await useAuthStore.getState().refresh();
  gate.resolve();
  await expect(pending).resolves.toBeUndefined();
  expect(useAuthStore.getState().accessToken).toBe(rotated.access_token);
});

it('does not return a successful response from a previous login', async () => {
  useAuthStore.getState().setSession(original);
  const gate = deferred();
  let sent = false;
  server.use(
    http.get('/api/private-result', async () => {
      sent = true;
      await gate.promise;
      return HttpResponse.json({ private: 'old account data' });
    }),
  );
  const pending = apiCall('/api/private-result', {
    schema: z.object({ private: z.string() }),
  }).catch((error: unknown) => error);
  await vi.waitFor(() => expect(sent).toBe(true));
  useAuthStore.getState().setSession(tokenFor(adminUser));
  gate.resolve();
  await expect(pending).resolves.toMatchObject({ code: 'session_changed' });
});

it.each(['json', 'text', 'blob', 'file'] as const)(
  'discards a late %s body after its response headers arrived under the old login',
  async (kind) => {
    useAuthStore.getState().setSession(original);
    const gate = deferred();
    const response = new Response('old account data');
    let reading = false;
    const waitForBody = async () => {
      reading = true;
      await gate.promise;
    };
    vi.spyOn(response, 'json').mockImplementation(async () => {
      await waitForBody();
      return { ok: true };
    });
    vi.spyOn(response, 'text').mockImplementation(async () => {
      await waitForBody();
      return 'private';
    });
    vi.spyOn(response, 'blob').mockImplementation(async () => {
      await waitForBody();
      return new Blob(['private']);
    });
    vi.spyOn(window, 'fetch').mockResolvedValue(response);
    const read = {
      json: () => apiCall('/api/private-result', { schema: z.object({ ok: z.boolean() }) }),
      text: () => apiText('/api/private-result'),
      blob: () => apiBlob('/api/private-result'),
      file: () => apiFile('/api/private-result'),
    };
    const pending = read[kind]().catch((error: unknown) => error);
    await vi.waitFor(() => expect(reading).toBe(true));
    useAuthStore.getState().setSession(tokenFor(adminUser));
    gate.resolve();
    await expect(pending).resolves.toMatchObject({ code: 'session_changed' });
  },
);

it.each(['other account', 'same account new family'])(
  'does not replay a binary upload when refresh discovers %s in another tab',
  async (kind) => {
    useAuthStore.getState().setSession(original);
    setCsrfCookie(CSRF_VALUE);
    const handler = vi.fn(() => expired());
    server.use(
      http.post('/api/private-upload', handler),
      http.post('/api/auth/refresh', () =>
        HttpResponse.json(
          kind === 'other account'
            ? tokenFor(adminUser)
            : tokenFor(plainUser, { familyId: 'new-login' }),
        ),
      ),
    );
    await expect(
      apiSend('/api/private-upload', { method: 'POST', rawBody: new Blob(['private']) }),
    ).rejects.toMatchObject({ status: 401 });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().accessToken).toBe(original.access_token);
  },
);
