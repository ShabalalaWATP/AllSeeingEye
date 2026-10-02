import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { fetchReportFile, fetchReportStix } from './reportDocuments';

it('preserves explicitly selected reviewed-source snapshots for document exports', async () => {
  applySession('user');
  const requests: URL[] = [];
  server.use(
    http.get('/api/reports/:id/export/docx', ({ request }) => {
      requests.push(new URL(request.url));
      return new HttpResponse('document');
    }),
  );
  await fetchReportFile('report', 7, 'docx', 'snapshot/with & punctuation');
  await fetchReportFile('report', 7, 'docx');
  expect(requests.map((url) => url.searchParams.get('version'))).toEqual(['7', '7']);
  expect(requests.map((url) => url.searchParams.get('source_snapshot_id'))).toEqual([
    'snapshot/with & punctuation',
    null,
  ]);
  expect([...requests[0]!.searchParams.keys()]).toEqual(['version', 'source_snapshot_id']);
});

it('requests STIX with its exact frozen version and marking without a reviewed-source overlay', async () => {
  applySession('user');
  let query = '';
  server.use(
    http.get('/api/reports/:id/stix', ({ request }) => {
      query = new URL(request.url).search;
      return new HttpResponse('{}', { headers: { 'Content-Type': 'application/stix+json' } });
    }),
  );
  const blob = await fetchReportStix('report', 7, 'amber');
  expect(query).toBe('?version=7&tlp=amber');
  expect(blob.type).toBe('application/stix+json');
});
