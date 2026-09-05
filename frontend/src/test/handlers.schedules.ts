/** MSW handlers for scheduled products. */
import { http, HttpResponse } from 'msw';

import { schedule } from './fixtures.schedules';

export const scheduleHandlers = [
  http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),

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
];
