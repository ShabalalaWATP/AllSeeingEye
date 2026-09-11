import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { reportJob, jobId } from '@/test/reportJobFixture';
import { apiError } from '@/test/handlers';
import { bindSession, resetSessionBinding } from './client';
import {
  createReportJob,
  controlReportJob,
  discardReportJob,
  fetchReportJob,
  type ReportJobCreate,
} from './reportJobs';

afterEach(resetSessionBinding);

it('never replays a discard automatically after session refresh', async () => {
  const discard = vi.fn(() => apiError(401, 'unauthenticated', 'Session expired.'));
  bindSession({
    getAccessToken: () => 'stale',
    refreshAccessToken: () => Promise.resolve('fresh'),
    onSessionLost: vi.fn(),
  });
  server.use(http.delete('/api/report-jobs/:id', discard));
  await expect(discardReportJob(jobId, new AbortController().signal)).rejects.toMatchObject({
    code: 'request_retry_required',
  });
  expect(discard).toHaveBeenCalledTimes(1);
});

it('requires explicit retry after refresh and sends the same idempotency key and payload', async () => {
  let token = 'stale';
  const requests: ReportJobCreate[] = [];
  bindSession({
    getAccessToken: () => token,
    refreshAccessToken: () => {
      token = 'fresh';
      return Promise.resolve(token);
    },
    onSessionLost: vi.fn(),
  });
  server.use(
    http.post('/api/report-jobs', async ({ request }) => {
      requests.push((await request.json()) as ReportJobCreate);
      return requests.length === 1
        ? apiError(401, 'unauthenticated', 'Session expired.')
        : HttpResponse.json(reportJob());
    }),
  );
  const body: ReportJobCreate = {
    request_id: jobId,
    report: {
      template: 'ask',
      question: 'What is known?',
      devils_advocacy: false,
      report_language: 'en',
      report_style: 'assessment',
      research_web_search: false,
      research_focus: 'general',
      disclose_area_to_provider: false,
    },
  };
  await expect(createReportJob(body, new AbortController().signal)).rejects.toMatchObject({
    code: 'request_retry_required',
  });
  expect(requests).toHaveLength(1);
  await expect(createReportJob(body, new AbortController().signal)).resolves.toMatchObject({
    id: jobId,
  });
  expect(requests).toEqual([body, body]);
});

it.each(['read', 'pause', 'resume'] as const)(
  'rejects a mismatched %s job response',
  async (action) => {
    const response = () =>
      HttpResponse.json(reportJob({ id: '77777777-7777-4777-8777-777777777777' }));
    server.use(
      http.get('/api/report-jobs/:id', response),
      http.post('/api/report-jobs/:id/:action', response),
    );
    const signal = new AbortController().signal;
    await expect(
      action === 'read' ? fetchReportJob(jobId, signal) : controlReportJob(jobId, action, signal),
    ).rejects.toMatchObject({ code: 'invalid_response' });
  },
);
