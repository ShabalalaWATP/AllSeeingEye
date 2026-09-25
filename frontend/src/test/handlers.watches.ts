/**
 * MSW handlers for the list endpoints the Watches hub reads that have no default
 * handler. Tests opt in with server.use(...watchHandlers) so other suites still fail
 * loudly on an unexpected brief or monitor request.
 */
import { http, HttpResponse } from 'msw';

import type { BriefSummary } from '@/lib/api/researchBriefSchema';
import type { Indicator } from '@/lib/api/warning';

import { annotationMonitor } from './fixtures.monitors';
import { indicator } from './fixtures.warning';

export const briefSummary: BriefSummary = {
  id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
  revision: 4,
  owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
  team_id: null,
  title: 'Baltic shipping disruption',
  schema_version: 1,
  origin: 'authored',
  published: false,
  created_at: '2026-09-14T10:00:00Z',
  revised_at: '2026-09-14T11:00:00Z',
};

export const areaIndicator: Indicator = {
  ...indicator,
  id: 'c4c4c4c4-c4c4-4c4c-8c4c-c4c4c4c4c4c4',
  name: 'Donbas box',
  countries: [],
  bbox: [36, 47, 39, 49],
  updated_at: '2026-09-06T10:00:00Z',
};

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
