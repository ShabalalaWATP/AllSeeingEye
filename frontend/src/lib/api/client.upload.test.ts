import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiBlob, apiCall, apiText, bindSession, resetSessionBinding } from './client';

const schema = z.object({ ok: z.boolean() });
const success = () => Response.json({ ok: true });

describe('abortable raw API requests', () => {
  afterEach(() => {
    resetSessionBinding();
    vi.restoreAllMocks();
  });

  it('sends the original binary body with bearer auth and cookies', async () => {
    const file = new File(['raw content'], 'a.txt');
    const fetch = vi.spyOn(window, 'fetch').mockResolvedValue(success());
    bindSession({
      getAccessToken: () => 'token',
      refreshAccessToken: () => Promise.resolve(null),
      onSessionLost: vi.fn(),
    });
    await apiCall('/api/research/inputs', { schema, method: 'POST', rawBody: file });
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      body: file,
      credentials: 'include',
      headers: { 'Content-Type': 'application/octet-stream', Authorization: 'Bearer token' },
    });
  });

  it('reuses the Blob and abort signal when refreshing a rejected request once', async () => {
    const file = new File(['raw'], 'a.txt');
    const controller = new AbortController();
    const fetch = vi
      .spyOn(window, 'fetch')
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(success());
    bindSession({
      getAccessToken: () => 'old',
      refreshAccessToken: () => Promise.resolve('new'),
      onSessionLost: vi.fn(),
    });
    await apiCall('/api/research/inputs', {
      schema,
      method: 'POST',
      rawBody: file,
      signal: controller.signal,
    });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[1]?.[1]).toMatchObject({
      body: file,
      signal: controller.signal,
      headers: { Authorization: 'Bearer new' },
    });
  });

  it('rejects an ambiguous JSON plus binary body without issuing a request', async () => {
    const fetch = vi.spyOn(window, 'fetch');
    await expect(
      apiCall('/api/x', { schema, body: {}, rawBody: new Blob(['x']) }),
    ).rejects.toMatchObject({ code: 'invalid_request' });
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not retry a request cancelled while refreshing', async () => {
    const controller = new AbortController();
    const fetch = vi.spyOn(window, 'fetch').mockResolvedValue(new Response(null, { status: 401 }));
    bindSession({
      getAccessToken: () => 'old',
      refreshAccessToken: () => {
        controller.abort();
        return Promise.resolve('new');
      },
      onSessionLost: vi.fn(),
    });
    await expect(apiCall('/api/x', { schema, signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('preserves AbortError for cancelled fetches instead of showing a network failure', async () => {
    const controller = new AbortController();
    vi.spyOn(window, 'fetch').mockImplementation(() => {
      controller.abort();
      return Promise.reject(new DOMException('Cancelled', 'AbortError'));
    });
    await expect(apiCall('/api/x', { schema, signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    });
  });

  it('does not start a fetch when already cancelled', async () => {
    const controller = new AbortController();
    controller.abort();
    const fetch = vi.spyOn(window, 'fetch');
    await expect(apiCall('/api/x', { schema, signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it('keeps Markdown and binary exports working through the extended client', async () => {
    const fetch = vi
      .spyOn(window, 'fetch')
      .mockResolvedValueOnce(new Response('report'))
      .mockResolvedValueOnce(new Response('binary'));
    await expect(apiText('/api/report')).resolves.toBe('report');
    const blob = await apiBlob('/api/document');
    expect(blob.size).toBe(6);
    expect(fetch.mock.calls[0]?.[1]?.headers).toMatchObject({
      Accept: 'text/plain, text/markdown',
    });
    expect(fetch.mock.calls[1]?.[1]?.headers).toMatchObject({ Accept: 'application/octet-stream' });
  });

  it('preserves browser AbortError without a caller signal', async () => {
    vi.spyOn(window, 'fetch').mockRejectedValue(new DOMException('Aborted', 'AbortError'));
    await expect(apiCall('/api/x', { schema })).rejects.toMatchObject({ name: 'AbortError' });
  });

  it('fails safely when a request has no active session bridge', async () => {
    resetSessionBinding();
    vi.spyOn(window, 'fetch').mockResolvedValue(new Response(null, { status: 401 }));
    await expect(apiCall('/api/x', { schema })).rejects.toMatchObject({ status: 401 });
  });
});
