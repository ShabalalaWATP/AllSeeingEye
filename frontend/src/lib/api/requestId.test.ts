import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { server } from '@/test/server';

import { apiSend } from './client';

it('retains the support reference alongside the existing API error fields', async () => {
  server.use(
    http.get('/api/failing', () =>
      HttpResponse.json(
        {
          error: {
            code: 'internal_error',
            message: 'Please try again.',
            request_id: 'support-1234',
          },
        },
        { status: 500 },
      ),
    ),
  );
  await expect(apiSend('/api/failing', { auth: false })).rejects.toMatchObject({
    code: 'internal_error',
    message: 'Please try again.',
    requestId: 'support-1234',
    status: 500,
  });
});
