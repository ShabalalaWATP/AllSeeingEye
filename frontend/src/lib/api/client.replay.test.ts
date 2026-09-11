import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { waitFor } from '@testing-library/react';
import { z } from 'zod';

import { apiError } from '@/test/handlers';
import { server } from '@/test/server';
import { apiCall, bindSession, resetSessionBinding } from './client';

const schema = z.object({ ok: z.boolean() });
const expired = () => apiError(401, 'unauthenticated', 'Sign in required.');

describe('explicit request replay policy', () => {
  afterEach(resetSessionBinding);

  it('refreshes for the next explicit request without replaying a costly POST', async () => {
    const seen: (string | null)[] = [];
    let token = 'expired';
    const refresh = vi.fn(() => Promise.resolve((token = 'fresh')));
    const lost = vi.fn();
    bindSession({ getAccessToken: () => token, refreshAccessToken: refresh, onSessionLost: lost });
    server.use(
      http.post('/api/costly', ({ request }) => {
        seen.push(request.headers.get('Authorization'));
        return seen.length === 1 ? expired() : HttpResponse.json({ ok: true });
      }),
    );

    const options = {
      method: 'POST' as const,
      body: { question: 'Test' },
      schema,
      retryAfterRefresh: false,
    };
    await expect(apiCall('/api/costly', options)).rejects.toMatchObject({
      status: 409,
      code: 'request_retry_required',
    });
    expect(seen).toEqual(['Bearer expired']);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(lost).not.toHaveBeenCalled();

    await expect(apiCall('/api/costly', options)).resolves.toEqual({ ok: true });
    expect(seen).toEqual(['Bearer expired', 'Bearer fresh']);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it('honours cancellation while refreshing and never resends the body', async () => {
    let completeRefresh!: (token: string | null) => void;
    const refresh = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          completeRefresh = resolve;
        }),
    );
    const lost = vi.fn();
    bindSession({
      getAccessToken: () => 'expired',
      refreshAccessToken: refresh,
      onSessionLost: lost,
    });
    let posts = 0;
    server.use(
      http.post('/api/costly', () => {
        posts++;
        return expired();
      }),
    );
    const controller = new AbortController();
    const outcome = apiCall('/api/costly', {
      method: 'POST',
      schema,
      retryAfterRefresh: false,
      signal: controller.signal,
    }).catch((error: unknown) => error);
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    controller.abort();
    completeRefresh('fresh');
    await expect(outcome).resolves.toBe(controller.signal.reason);
    expect(posts).toBe(1);
    expect(lost).not.toHaveBeenCalled();
  });

  it('still clears a lost session when refresh fails with replay disabled', async () => {
    const lost = vi.fn();
    bindSession({
      getAccessToken: () => 'expired',
      refreshAccessToken: () => Promise.resolve(null),
      onSessionLost: lost,
    });
    let posts = 0;
    server.use(
      http.post('/api/costly', () => {
        posts++;
        return expired();
      }),
    );
    await expect(
      apiCall('/api/costly', { method: 'POST', schema, retryAfterRefresh: false }),
    ).rejects.toMatchObject({ status: 401, code: 'unauthenticated' });
    expect(posts).toBe(1);
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it('preserves default POST refresh and replay behaviour', async () => {
    const refresh = vi.fn(() => Promise.resolve('fresh'));
    bindSession({
      getAccessToken: () => 'expired',
      refreshAccessToken: refresh,
      onSessionLost: vi.fn(),
    });
    let posts = 0;
    server.use(
      http.post('/api/ordinary', () => {
        posts++;
        return posts === 1 ? expired() : HttpResponse.json({ ok: true });
      }),
    );
    await expect(apiCall('/api/ordinary', { method: 'POST', schema })).resolves.toEqual({
      ok: true,
    });
    expect(posts).toBe(2);
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
