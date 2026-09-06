import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { verifySession } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';

it('checks the explicit bearer without refreshing or clearing a newer session on401', async () => {
  let received: string | null = null;
  let refreshes = 0;
  server.use(
    http.get('/api/me', ({ request }) => {
      received = request.headers.get('Authorization');
      useAuthStore.getState().setSession(tokenFor(plainUser));
      return HttpResponse.json(
        { error: { code: 'unauthenticated', message: 'Expired' } },
        { status: 401 },
      );
    }),
    http.post('/api/auth/refresh', () => {
      refreshes++;
      return HttpResponse.json(tokenFor(adminUser));
    }),
  );
  useAuthStore.getState().setSession(tokenFor(adminUser));
  await expect(verifySession('captured-token', new AbortController().signal)).rejects.toMatchObject(
    { status: 401 },
  );
  expect(received).toBe('Bearer captured-token');
  expect(refreshes).toBe(0);
  expect(useAuthStore.getState().user?.id).toBe(plainUser.id);
  expect(useAuthStore.getState().accessToken).toBe(tokenFor(plainUser).access_token);
});

it('honours an aborted captured request before sending any verification', async () => {
  let calls = 0;
  server.use(
    http.get('/api/me', () => {
      calls++;
      return HttpResponse.json(adminUser);
    }),
  );
  const controller = new AbortController();
  controller.abort();
  await expect(verifySession('captured-token', controller.signal)).rejects.toMatchObject({
    name: 'AbortError',
  });
  expect(calls).toBe(0);
});
