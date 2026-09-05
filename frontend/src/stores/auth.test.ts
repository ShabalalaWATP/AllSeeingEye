import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { setCsrfCookie } from '@/test/env';
import {
  ADMIN_TOKEN,
  CSRF_VALUE,
  USER_PASSWORD,
  USER_TOKEN,
  adminUser,
  plainUser,
} from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { selectIsAdmin, useAuthStore } from './auth';

describe('auth store', () => {
  it('bootstraps an authenticated session through the silent refresh', async () => {
    setCsrfCookie(CSRF_VALUE);
    let header: string | null = null;
    server.use(
      http.post('/api/auth/refresh', ({ request }) => {
        header = request.headers.get('X-CSRF-Token');
        return HttpResponse.json({
          access_token: ADMIN_TOKEN,
          token_type: 'bearer',
          expires_in: 900,
          user: adminUser,
        });
      }),
    );
    await useAuthStore.getState().bootstrap();
    expect(header).toBe(CSRF_VALUE);
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      accessToken: ADMIN_TOKEN,
      user: adminUser,
      pendingRefresh: null,
    });
  });

  it('skips the refresh entirely when no CSRF cookie exists', async () => {
    let calls = 0;
    server.use(
      http.post('/api/auth/refresh', () => {
        calls += 1;
        return apiError(403, 'csrf_failed', 'Missing CSRF token.');
      }),
    );
    await useAuthStore.getState().bootstrap();
    expect(calls).toBe(0);
    expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', accessToken: null });
  });

  it('ends anonymous when the refresh is rejected', async () => {
    setCsrfCookie(CSRF_VALUE);
    server.use(http.post('/api/auth/refresh', () => apiError(401, 'invalid_refresh', 'Expired.')));
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState()).toMatchObject({
      status: 'anonymous',
      accessToken: null,
      user: null,
    });
  });

  it('deduplicates concurrent refreshes', async () => {
    setCsrfCookie(CSRF_VALUE);
    let calls = 0;
    server.use(
      http.post('/api/auth/refresh', () => {
        calls += 1;
        return HttpResponse.json({
          access_token: ADMIN_TOKEN,
          token_type: 'bearer',
          expires_in: 900,
          user: adminUser,
        });
      }),
    );
    const store = useAuthStore.getState();
    const [first, second] = await Promise.all([store.refresh(), store.refresh()]);
    expect(first).toBe(ADMIN_TOKEN);
    expect(second).toBe(ADMIN_TOKEN);
    expect(calls).toBe(1);
  });

  it('keeps the access token in memory only after login', async () => {
    await useAuthStore.getState().login(plainUser.email, USER_PASSWORD);
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      accessToken: USER_TOKEN,
      user: plainUser,
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).not.toContain(USER_TOKEN);
  });

  it('surfaces invalid credentials without changing the session', async () => {
    await expect(
      useAuthStore.getState().login('nobody@example.com', 'wrong'),
    ).rejects.toMatchObject({
      code: 'invalid_credentials',
    });
    expect(useAuthStore.getState().status).toBe('unknown');
  });

  it('logs out with the CSRF header and clears the session', async () => {
    setCsrfCookie(CSRF_VALUE);
    let header: string | null = null;
    server.use(
      http.post('/api/auth/logout', ({ request }) => {
        header = request.headers.get('X-CSRF-Token');
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await useAuthStore.getState().login(plainUser.email, USER_PASSWORD);
    await useAuthStore.getState().logout();
    expect(header).toBe(CSRF_VALUE);
    expect(useAuthStore.getState()).toMatchObject({ status: 'anonymous', accessToken: null });
  });

  it('clears the session even when the logout request fails', async () => {
    server.use(http.post('/api/auth/logout', () => apiError(500, 'server_error', 'Boom.')));
    await useAuthStore.getState().login(plainUser.email, USER_PASSWORD);
    await useAuthStore.getState().logout();
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it('selects the admin role', () => {
    expect(selectIsAdmin(useAuthStore.getState())).toBe(false);
    useAuthStore.getState().setSession({
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
      expires_in: 900,
      user: adminUser,
    });
    expect(selectIsAdmin(useAuthStore.getState())).toBe(true);
  });
});
