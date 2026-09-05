/** MSW handlers for the warning API: indicators and alerts. */
import { http, HttpResponse } from 'msw';

import { acknowledgedAlert, alert, indicator } from './fixtures.warning';

interface IndicatorBody {
  name: string;
  countries?: string[];
  keywords?: string[];
  categories?: string[];
  threshold?: number;
  window_minutes?: number;
  report_template?: string | null;
}

const notFound = (what: string) =>
  HttpResponse.json(
    { error: { code: 'not_found', message: `${what} not found.` } },
    { status: 404 },
  );

export const warningHandlers = [
  http.get('/api/warning/indicators', () => HttpResponse.json({ items: [indicator] })),

  http.post('/api/warning/indicators', async ({ request }) => {
    const body = (await request.json()) as IndicatorBody;
    return HttpResponse.json(
      {
        ...indicator,
        id: 'c3c3c3c3-c3c3-4c3c-8c3c-c3c3c3c3c3c3',
        name: body.name,
        countries: body.countries ?? [],
        keywords: body.keywords ?? [],
        categories: body.categories ?? [],
        threshold: body.threshold ?? 1,
        window_minutes: body.window_minutes ?? 60,
        report_template: body.report_template ?? null,
      },
      { status: 201 },
    );
  }),

  http.put('/api/warning/indicators/:id', async ({ request, params }) => {
    if (params.id !== indicator.id) return notFound('Indicator');
    const body = (await request.json()) as IndicatorBody & { enabled?: boolean };
    return HttpResponse.json({ ...indicator, ...body });
  }),

  http.delete('/api/warning/indicators/:id', ({ params }) =>
    params.id === indicator.id ? new HttpResponse(null, { status: 204 }) : notFound('Indicator'),
  ),

  http.get('/api/warning/alerts', () =>
    HttpResponse.json({ items: [alert, acknowledgedAlert], unacknowledged: 1 }),
  ),

  http.post('/api/warning/alerts/:id/ack', ({ params }) =>
    params.id === alert.id
      ? HttpResponse.json({
          ...alert,
          acknowledged_at: '2026-09-05T12:00:00Z',
          acknowledged_by: '22222222-2222-4222-8222-222222222222',
        })
      : notFound('Alert'),
  ),
];
