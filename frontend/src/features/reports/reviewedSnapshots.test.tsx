import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ReviewedSnapshot, SourceSnapshotSummary } from '@/lib/api/sourceReviews';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { report } from '@/test/fixtures.reports';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { ReviewedSnapshots } from './ReviewedSnapshots';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

const reportId = report.report.id;
const base = `/api/reports/${reportId}/versions/1/source-assessment-snapshots`;
const snapshotId = '88888888-8888-4888-8888-000000000001';
const summary: SourceSnapshotSummary = {
  id: snapshotId,
  report_id: reportId,
  report_version_id: '66666666-6666-4666-8666-666666666666',
  authored_by: plainUser.id,
  created_at: '2026-09-30T12:00:00Z',
  decisions: 2,
  subjects: { KJ1: 'ground-activity' },
};
const snapshot: ReviewedSnapshot = {
  id: snapshotId,
  report_version_id: summary.report_version_id,
  authored_by: plainUser.id,
  created_at: summary.created_at,
  projection: {
    evidence: [{ capture_id: 'c1', label: 'E1' }],
    claims: [{ claim_id: 'k1', judgement_id: 'KJ1' }],
    assessments: [
      {
        evidence_id: 'c1',
        claim_id: 'k1',
        source_id: 'bbc_world',
        subject: 'ground-activity',
        reliability: 'A',
        credibility: 6,
        source_revision: { review: { id: '00000000-0000-4000-8000-000000000001' } },
        assertion_revision: null,
        authenticity: null,
      },
    ],
  },
};

function serve(snapshots: SourceSnapshotSummary[], options: { missing?: boolean } = {}) {
  const posts: unknown[] = [];
  const exports: string[] = [];
  let listed = snapshots;
  server.use(
    http.get(base, () => HttpResponse.json({ snapshots: listed, limit: 20 })),
    http.post(base, async ({ request }) => {
      posts.push(await request.json());
      listed = [summary, ...listed];
      return HttpResponse.json({ ...snapshot }, { status: 201 });
    }),
    http.get(`${base}/:id`, () =>
      options.missing ? apiError(404, 'not_found', 'Not found.') : HttpResponse.json(snapshot),
    ),
    http.get('/api/reports/:id/export/:format', ({ request }) => {
      exports.push(request.url);
      return HttpResponse.arrayBuffer(new ArrayBuffer(4), {
        headers: { 'Content-Type': 'application/pdf' },
      });
    }),
  );
  return { posts, exports };
}

function renderSnapshots(canWrite = true) {
  return render(
    <ReviewedSnapshots
      reportId={reportId}
      version={1}
      title="Kharkiv"
      judgements={report.version.body.key_judgements}
      canWrite={canWrite}
      reviewer={(id) => (id === plainUser.id ? 'You' : 'Another reviewer')}
    />,
  );
}

describe('reviewed source assessment snapshots', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: plainUser, status: 'authenticated' });
    vi.mocked(saveBinaryFile).mockClear();
  });

  it('creates a snapshot explicitly and leaves the original selected', async () => {
    const { posts } = serve([]);
    renderSnapshots();
    expect(await screen.findByText(/No reviewed snapshots for version 1/)).toBeVisible();
    await userEvent.type(screen.getByLabelText('Subject area for KJ1'), 'ground-activity');
    await userEvent.click(screen.getByRole('button', { name: 'Create reviewed snapshot' }));
    expect(await screen.findByText(/Snapshot created\. Select it/)).toBeVisible();
    expect(posts).toEqual([{ subjects: { KJ1: 'ground-activity' } }]);
    const choices = screen.getByRole('radiogroup', { name: 'Source assessment to view' });
    expect(
      within(choices).getByRole('radio', { name: /Original frozen assessment/ }),
    ).toBeChecked();
    expect(within(choices).getByRole('radio', { name: /2 reviewer decisions/ })).not.toBeChecked();
  });

  it('views and exports only with the selected snapshot', async () => {
    const { exports } = serve([summary]);
    renderSnapshots();
    const choice = await screen.findByRole('radio', { name: /2 reviewer decisions/ });
    expect(screen.queryByRole('button', { name: /PDF with this snapshot/ })).toBeNull();
    await userEvent.click(choice);
    const table = await screen.findByRole('table', { name: /Reviewed source assessment/ });
    expect(within(table).getByText('A: completely reliable')).toBeVisible();
    expect(within(table).getByText('6: truth cannot be judged')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Export PDF with this snapshot' }));
    await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
    expect(new URL(exports[0]!).searchParams.get('source_snapshot_id')).toBe(snapshotId);
    expect(new URL(exports[0]!).searchParams.get('version')).toBe('1');
    await userEvent.click(screen.getByRole('radio', { name: /Original frozen assessment/ }));
    expect(screen.queryByRole('table', { name: /Reviewed source assessment/ })).toBeNull();
  });

  it('reports an unavailable snapshot without substituting another', async () => {
    serve([summary], { missing: true });
    renderSnapshots(false);
    await userEvent.click(await screen.findByRole('radio', { name: /2 reviewer decisions/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/snapshot is unavailable/i);
    expect(screen.queryByRole('button', { name: /with this snapshot/ })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Create reviewed snapshot' })).toBeNull();
  });

  it('shows the snapshot limit and list errors', async () => {
    serve(
      Array.from({ length: 20 }, (_, index) => ({
        ...summary,
        id: `${snapshotId.slice(0, -2)}${String(index).padStart(2, '0')}`,
      })),
    );
    renderSnapshots();
    expect(await screen.findByText(/reached its 20-snapshot limit/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Create reviewed snapshot' })).toBeNull();
    server.use(
      http.get(base, () => apiError(404, 'not_found', 'The requested item does not exist.')),
    );
    renderSnapshots();
    expect(await screen.findByText(/Reviewed snapshots are unavailable/)).toBeVisible();
  });
});
