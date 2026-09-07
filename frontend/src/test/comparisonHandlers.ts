import { http, HttpResponse } from 'msw';
import { server } from './server';
import { report } from './fixtures';
import { comparisonClaim, comparisonClaimAfter } from './fixtures.comparisons';
export function comparisonSources() {
  server.use(
    http.get('/api/reports', () =>
      HttpResponse.json({ items: [{ ...report.report, latest_version: 2 }] }),
    ),
    http.get('/api/reports/:id', ({ params, request }) =>
      HttpResponse.json({
        report: { ...report.report, id: String(params.id), latest_version: 2 },
        version: {
          ...report.version,
          number: Number(new URL(request.url).searchParams.get('version') ?? 1),
        },
      }),
    ),
    http.get('/api/claims', () =>
      HttpResponse.json({ items: [comparisonClaimAfter], total: 1, limit: 20, offset: 0 }),
    ),
    http.get('/api/claims/claim-1/revisions/:id', ({ params }) =>
      HttpResponse.json({
        root: {
          id: 'claim-1',
          report_id: report.report.id,
          report_version_id: 'version-1',
          report_version_number: 1,
          created_by: 'user-1',
          team_id: null,
          evidence_sha256: 'hash',
          latest_revision_id: comparisonClaimAfter.id,
          created_at: comparisonClaim.created_at,
        },
        revision: params.id === comparisonClaim.id ? comparisonClaim : comparisonClaimAfter,
      }),
    ),
  );
}
