import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { apiCall, apiSend, bindSession, resetSessionBinding } from './client';
import { ApiError } from './errors';

const schema = z.object({ ok: z.boolean() });

describe('api client', () => {
  afterEach(() => {
    resetSessionBinding();
  });

  it('returns a validated JSON body', async () => {
    server.use(http.get('/api/thing', () => HttpResponse.json({ ok: true })));
    await expect(apiCall('/api/thing', { schema })).resolves.toEqual({ ok: true });
  });

  it('sends JSON bodies with credentials and the bearer token', async () => {
    let seen: { auth: string | null; type: string | null; body: unknown } | null = null;
    server.use(
      http.post('/api/thing', async ({ request }) => {
        seen = {
          auth: request.headers.get('Authorization'),
          type: request.headers.get('Content-Type'),
          body: await request.json(),
        };
        return HttpResponse.json({ ok: true });
      }),
    );
    bindSession({
      getAccessToken: () => 'token-1',
      refreshAccessToken: () => Promise.resolve(null),
      onSessionLost: vi.fn(),
    });
    await apiCall('/api/thing', { method: 'POST', body: { a: 1 }, schema });
    expect(seen).toEqual({ auth: 'Bearer token-1', type: 'application/json', body: { a: 1 } });
  });

  it('parses the error envelope including fields and Retry-After', async () => {
    server.use(
      http.get('/api/thing', () =>
        apiError(429, 'rate_limited', 'Slow down.', { email: 'bad' }, { 'Retry-After': '30' }),
      ),
    );
    const error: unknown = await apiCall('/api/thing', { schema }).catch(
      (caught: unknown) => caught,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 429,
      code: 'rate_limited',
      message: 'Slow down.',
      fields: { email: 'bad' },
      retryAfterSeconds: 30,
    });
  });

  it('falls back to unknown_error for bodies that are not an envelope', async () => {
    server.use(
      http.get('/api/thing', () =>
        HttpResponse.text('nope', { status: 500, headers: { 'Retry-After': 'x' } }),
      ),
    );
    await expect(apiCall('/api/thing', { schema })).rejects.toMatchObject({
      status: 500,
      code: 'unknown_error',
      retryAfterSeconds: null,
    });
  });

  it('rejects bodies that fail schema validation', async () => {
    server.use(http.get('/api/thing', () => HttpResponse.json({ ok: 'yes' })));
    await expect(apiCall('/api/thing', { schema })).rejects.toMatchObject({
      code: 'invalid_response',
    });
  });

  it('reports network failures as network_error', async () => {
    server.use(http.get('/api/thing', () => HttpResponse.error()));
    await expect(apiCall('/api/thing', { schema })).rejects.toMatchObject({
      status: 0,
      code: 'network_error',
    });
  });

  it('refreshes once and retries after a 401', async () => {
    let calls = 0;
    server.use(
      http.get('/api/thing', ({ request }) => {
        calls += 1;
        if (request.headers.get('Authorization') === 'Bearer fresh') {
          return HttpResponse.json({ ok: true });
        }
        return apiError(401, 'unauthenticated', 'Sign in required.');
      }),
    );
    const refresh = vi.fn(() => Promise.resolve('fresh'));
    const lost = vi.fn();
    bindSession({
      getAccessToken: () => 'stale',
      refreshAccessToken: refresh,
      onSessionLost: lost,
    });
    await expect(apiCall('/api/thing', { schema })).resolves.toEqual({ ok: true });
    expect(calls).toBe(2);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(lost).not.toHaveBeenCalled();
  });

  it('gives up and reports a lost session when the refresh fails', async () => {
    server.use(http.get('/api/thing', () => apiError(401, 'unauthenticated', 'Sign in required.')));
    const lost = vi.fn();
    bindSession({
      getAccessToken: () => 'stale',
      refreshAccessToken: () => Promise.resolve(null),
      onSessionLost: lost,
    });
    await expect(apiCall('/api/thing', { schema })).rejects.toMatchObject({
      code: 'unauthenticated',
    });
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it('reports a lost session when the retried request is rejected too', async () => {
    let calls = 0;
    server.use(
      http.get('/api/thing', () => {
        calls += 1;
        return apiError(401, 'unauthenticated', 'Sign in required.');
      }),
    );
    const lost = vi.fn();
    bindSession({
      getAccessToken: () => 'stale',
      refreshAccessToken: () => Promise.resolve('fresh'),
      onSessionLost: lost,
    });
    await expect(apiCall('/api/thing', { schema })).rejects.toMatchObject({ status: 401 });
    expect(calls).toBe(2);
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it('never refreshes when auth is disabled for the call', async () => {
    server.use(http.get('/api/thing', () => apiError(401, 'invalid_refresh', 'Expired.')));
    const refresh = vi.fn(() => Promise.resolve('fresh'));
    bindSession({
      getAccessToken: () => 'stale',
      refreshAccessToken: refresh,
      onSessionLost: vi.fn(),
    });
    await expect(apiCall('/api/thing', { schema, auth: false })).rejects.toMatchObject({
      code: 'invalid_refresh',
    });
    expect(refresh).not.toHaveBeenCalled();
  });

  it('apiSend resolves on 204 and throws on failure', async () => {
    server.use(
      http.post('/api/ok', () => new HttpResponse(null, { status: 204 })),
      http.post('/api/bad', () => apiError(404, 'not_found', 'Missing.')),
    );
    await expect(apiSend('/api/ok', { method: 'POST' })).resolves.toBeUndefined();
    await expect(apiSend('/api/bad', { method: 'POST' })).rejects.toMatchObject({
      code: 'not_found',
    });
  });
});
