/**
 * MSW handlers for the list endpoints the Watches hub reads that have no default
 * handler. Tests opt in with server.use(...watchHandlers) so other suites still fail
 * loudly on an unexpected brief or monitor request.
 */
import { http, HttpResponse } from 'msw';

import { annotationMonitor } from './fixtures.monitors';
import { indicator } from './fixtures.warning';
import { areaIndicator, briefSummary } from './fixtures.watches';

export { areaIndicator, briefSummary } from './fixtures.watches';

export const watchHandlers = [
  http.get('/api/research/briefs', () =>
    HttpResponse.json({ items: [briefSummary], limit: 50, offset: 0 }),
  ),
  http.get('/api/annotation-monitors', () =>
    HttpResponse.json({ items: [annotationMonitor], total: 1, offset: 0, limit: 20 }),
  ),
  http.get('/api/warning/indicators', () =>
    HttpResponse.json({ items: [indicator, areaIndicator] }),
  ),
];
