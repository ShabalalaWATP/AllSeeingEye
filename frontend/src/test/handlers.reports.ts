import { http, HttpResponse } from 'msw';

import { report, reportSummary, reportTemplates } from './fixtures';
import { apiError } from './handlers';

export const reportHandlers = [
  http.get('/api/reports/templates', () => HttpResponse.json({ items: reportTemplates })),

  http.get('/api/reports', () => HttpResponse.json({ items: [reportSummary] })),

  http.post('/api/reports', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const id = '99999999-9999-4999-8999-999999999999';
    return HttpResponse.json(
      { ...report, report: { ...reportSummary, id, template: String(body.template) } },
      { status: 201 },
    );
  }),

  http.get('/api/reports/:id', ({ params }) => {
    if (params.id === reportSummary.id) return HttpResponse.json(report);
    if (params.id === '99999999-9999-4999-8999-999999999999') {
      return HttpResponse.json({ ...report, report: { ...reportSummary, id: params.id } });
    }
    return apiError(404, 'not_found', 'Report not found.');
  }),

  http.post('/api/reports/:id/versions', ({ params }) =>
    HttpResponse.json(
      {
        report: { ...reportSummary, id: String(params.id), latest_version: 2 },
        version: { ...report.version, number: 2 },
      },
      { status: 201 },
    ),
  ),

  http.get('/api/reports/:id/markdown', () =>
    HttpResponse.text('# Intelligence summary: Ukraine', {
      headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
    }),
  ),

  http.delete('/api/reports/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/report-search', () =>
    HttpResponse.json({
      available: false,
      indexed: 0,
      total: 1,
      limit: 1000,
      batch_size: 8,
    }),
  ),
];
