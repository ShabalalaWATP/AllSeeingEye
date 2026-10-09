import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { apiSend } from '@/lib/api/client';
import { setCsrfCookie } from '@/test/env';
import { CSRF_VALUE, plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { useAuthStore } from './auth';

it('refreshes through the bound auth store and retries with the rotated bearer token', async () => {
  const original = tokenFor(plainUser);
  const refreshed = tokenFor(plainUser, { revision: 'refreshed' });
  const authorisation: (string | null)[] = [];
  const csrf: (string | null)[] = [];
  server.use(
    http.get('/api/auth-boundary', ({ request }) => {
      const token = request.headers.get('Authorization');
      authorisation.push(token);
      return token === `Bearer ${refreshed.access_token}`
        ? new HttpResponse(null, { status: 204 })
        : apiError(401, 'unauthenticated', 'Refresh required.');
    }),
    http.post('/api/auth/refresh', ({ request }) => {
      csrf.push(request.headers.get('X-CSRF-Token'));
      return HttpResponse.json(refreshed);
    }),
  );
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);

  await expect(apiSend('/api/auth-boundary')).resolves.toBeUndefined();

  expect(authorisation).toEqual([
    `Bearer ${original.access_token}`,
    `Bearer ${refreshed.access_token}`,
  ]);
  expect(csrf).toEqual([CSRF_VALUE]);
  expect(useAuthStore.getState()).toMatchObject({
    status: 'authenticated',
    user: plainUser,
    accessToken: refreshed.access_token,
    pendingRefresh: null,
  });
});

it('clears the actual store when the server also rejects a successfully refreshed session', async () => {
  const original = tokenFor(plainUser);
  const refreshed = tokenFor(plainUser, { revision: 'rejected' });
  const authorisation: (string | null)[] = [];
  let refreshes = 0;
  server.use(
    http.get('/api/auth-boundary', ({ request }) => {
      authorisation.push(request.headers.get('Authorization'));
      return apiError(401, 'unauthenticated', 'Session revoked.');
    }),
    http.post('/api/auth/refresh', () => {
      refreshes += 1;
      return HttpResponse.json(refreshed);
    }),
  );
  setCsrfCookie(CSRF_VALUE);
  useAuthStore.getState().setSession(original);

  await expect(apiSend('/api/auth-boundary')).rejects.toMatchObject({ status: 401 });

  expect(refreshes).toBe(1);
  expect(authorisation).toEqual([
    `Bearer ${original.access_token}`,
    `Bearer ${refreshed.access_token}`,
  ]);
  expect(useAuthStore.getState()).toMatchObject({
    status: 'anonymous',
    user: null,
    accessToken: null,
    pendingRefresh: null,
  });
});
