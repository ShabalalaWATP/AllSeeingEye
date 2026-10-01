import { http, HttpResponse } from 'msw';

import { bellSummary, noPreferences } from './fixtures.bell';

export const bellHandlers = [
  http.get('/api/bell', () => HttpResponse.json(bellSummary())),
  http.get('/api/bell/alerts/:id/destination', () =>
    HttpResponse.json({
      kind: 'alerts',
      available: true,
      report_id: null,
      monitor_id: null,
      transition_id: null,
      message: null,
    }),
  ),
  http.post('/api/bell/alerts/acknowledge', async ({ request }) => {
    const body = (await request.json()) as { alert_ids: string[] };
    return HttpResponse.json({ acknowledged: body.alert_ids, failed: [] });
  }),
  http.put('/api/bell/preferences', async ({ request }) => {
    const body = (await request.json()) as { muted_kinds: string[] };
    return HttpResponse.json({ ...noPreferences, muted_kinds: body.muted_kinds });
  }),
  http.delete('/api/bell/muted-rules/:id', () => HttpResponse.json(noPreferences)),
];
