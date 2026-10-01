import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { apiCall, resetSessionBinding } from './client';
import { describeError } from './errors';
import { parseRetryAfter } from './errorResponses';

const schema = z.object({ ok: z.boolean() });

async function failure(response: () => Response): Promise<unknown> {
  server.use(http.get('/api/thing', response));
  return apiCall('/api/thing', { schema }).catch((caught: unknown) => caught);
}

const bodies = {
  html: () => '<html><body><h1>502 Bad Gateway</h1><script>alert(1)</script></body></html>',
  empty: () => '',
  malformed: () => '{"error": {"code": ',
};

describe('unexpected HTTP responses', () => {
  afterEach(resetSessionBinding);

  describe.each([502, 503, 504])('a non-envelope %i', (status) => {
    it.each(Object.entries(bodies))(
      'explains a temporary outage for a %s body',
      async (_, body) => {
        const error = await failure(() => new HttpResponse(body(), { status }));
        expect(error).toMatchObject({ status, code: 'service_unavailable' });
        const message = describeError(error);
        expect(message).toContain('The service is temporarily unavailable.');
        expect(message).toContain('Please try again later.');
        expect(message).toContain(`Reference: HTTP ${String(status)}.`);
        expect(message).not.toMatch(/Bad Gateway|<|script|restart/i);
      },
    );
  });

  it('asks the user to reduce the size of a rejected submission', async () => {
    const error = await failure(() => new HttpResponse('<h1>Too large</h1>', { status: 413 }));
    expect(error).toMatchObject({ status: 413, code: 'payload_too_large' });
    const message = describeError(error);
    expect(message).toMatch(/too large/i);
    expect(message).toMatch(/reduce/i);
    expect(message).not.toContain('<h1>');
  });

  it('uses Retry-After seconds for a non-envelope 429', async () => {
    const error = await failure(
      () => new HttpResponse('slow down', { status: 429, headers: { 'Retry-After': '20' } }),
    );
    expect(error).toMatchObject({ status: 429, code: 'rate_limited', retryAfterSeconds: 20 });
    expect(describeError(error)).toBe('Too many attempts. Try again in 20 seconds.');
  });

  it('reads an HTTP-date Retry-After and rounds long waits to minutes', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-10-01T12:00:00Z'));
    try {
      const error = await failure(
        () =>
          new HttpResponse(null, {
            status: 429,
            headers: { 'Retry-After': 'Thu, 01 Oct 2026 12:05:00 GMT' },
          }),
      );
      expect(error).toMatchObject({ retryAfterSeconds: 300 });
      expect(describeError(error)).toBe('Too many attempts. Try again in about 5 minutes.');
    } finally {
      vi.useRealTimers();
    }
  });

  it('gives a cautious instruction when a 429 has no retry information', async () => {
    const error = await failure(() => new HttpResponse(null, { status: 429 }));
    expect(describeError(error)).toBe('Too many attempts. Wait a few minutes before trying again.');
  });

  it('uses plain wording for other unexpected responses and keeps the status secondary', async () => {
    const error = await failure(() => new HttpResponse('<pre>Traceback</pre>', { status: 500 }));
    expect(error).toMatchObject({ status: 500, code: 'unknown_error' });
    const message = describeError(error);
    expect(message.startsWith('The server could not complete the request.')).toBe(true);
    expect(message).toContain('Reference: HTTP 500.');
    expect(message).not.toMatch(/Traceback|<pre>/);
    expect(message).not.toMatch(/^The request failed with status/);
  });

  it('keeps valid envelope messages and field reasons unchanged', async () => {
    const error = await failure(() =>
      apiError(503, 'upstream_unavailable', 'An upstream service did not answer.', {
        name: 'Too long.',
      }),
    );
    expect(error).toMatchObject({
      code: 'upstream_unavailable',
      message: 'An upstream service did not answer.',
      fields: { name: 'Too long.' },
    });
    expect(describeError(error)).toBe('An upstream service did not answer.');
  });

  it('keeps usage-limit explanations for an enveloped 429', async () => {
    const error = await failure(() =>
      apiError(429, 'research_usage_limit', 'Your allowance resets tomorrow.', undefined, {
        'Retry-After': '3600',
      }),
    );
    expect(describeError(error)).toBe('Your allowance resets tomorrow.');
  });
});

describe('parseRetryAfter', () => {
  it.each([
    [null, null],
    ['x', null],
    ['-4', null],
    ['15', 15],
    ['Thu, 01 Oct 2020 12:00:00 GMT', 0],
  ])('reads %s as %s', (value, expected) => {
    expect(parseRetryAfter(value)).toBe(expected);
  });
});
