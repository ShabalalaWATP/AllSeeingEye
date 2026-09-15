/** MSW handlers for scheduled products. */
import { http, HttpResponse } from 'msw';

import { schedule } from './fixtures.schedules';

export const scheduleHandlers = [
  http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
  http.get('/api/schedules/usage', () =>
    HttpResponse.json({
      scope: 'owner',
      subscription_id: null,
      month_start: '2026-09-01T00:00:00Z',
      month_end: '2026-10-01T00:00:00Z',
      policy_version: 'subscription-monthly-budget-v1',
      used: { requests: 0, output_tokens: 0 },
      limit: { requests: 800, output_tokens: 24_000_000 },
    }),
  ),
  http.get('/api/schedules/:id/usage', ({ params }) =>
    HttpResponse.json({
      scope: 'subscription',
      subscription_id: params.id,
      month_start: '2026-09-01T00:00:00Z',
      month_end: '2026-10-01T00:00:00Z',
      policy_version: 'subscription-monthly-budget-v1',
      used: { requests: 0, output_tokens: 0 },
      limit: { requests: 240, output_tokens: 8_000_000 },
    }),
  ),

  http.post('/api/schedules', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      { ...schedule, ...body, id: 'e2e2e2e2-e2e2-4e2e-8e2e-e2e2e2e2e2e2', last_report_id: null },
      { status: 201 },
    );
  }),

  http.delete('/api/schedules/:id', ({ params }) =>
    params.id === schedule.id
      ? new HttpResponse(null, { status: 204 })
      : HttpResponse.json(
          { error: { code: 'not_found', message: 'Schedule not found.' } },
          { status: 404 },
        ),
  ),
  http.put('/api/schedules/:id', async ({ request }) =>
    HttpResponse.json({
      ...schedule,
      ...((await request.json()) as Record<string, unknown>),
    }),
  ),
  http.post('/api/schedules/:id/pause', () => HttpResponse.json({ ...schedule, enabled: false })),
  http.post('/api/schedules/:id/resume', () => HttpResponse.json({ ...schedule, enabled: true })),
];
