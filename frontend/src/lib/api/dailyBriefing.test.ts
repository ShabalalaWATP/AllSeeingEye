import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { apiError } from '@/test/handlers';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { bindSession, resetSessionBinding } from './client';
import { ensureDailyBriefing } from './dailyBriefing';

afterEach(resetSessionBinding);

it('validates the daily briefing envelope and refuses an invalid refresh date', async () => {
  server.use(
    http.post('/api/live-monitor/briefing', () =>
      HttpResponse.json({
        job: reportJob(),
        next_refresh_at: 'tomorrow',
        coverage_note: 'Connected sources.',
      }),
    ),
  );
  await expect(ensureDailyBriefing(new AbortController().signal)).rejects.toMatchObject({
    code: 'invalid_response',
  });
});

it('does not replay admission silently after session refresh', async () => {
  const start = vi.fn(() => apiError(401, 'unauthenticated', 'Session expired.'));
  bindSession({
    getAccessToken: () => 'stale',
    refreshAccessToken: () => Promise.resolve('fresh'),
    onSessionLost: vi.fn(),
  });
  server.use(http.post('/api/live-monitor/briefing', start));
  await expect(ensureDailyBriefing(new AbortController().signal)).rejects.toMatchObject({
    code: 'request_retry_required',
  });
  expect(start).toHaveBeenCalledTimes(1);
});
