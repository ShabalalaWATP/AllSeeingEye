import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as documents from '@/lib/api/reportDocuments';
import * as reports from '@/lib/api/reports';
import * as reviews from '@/lib/api/sourceReviews';
import type { ReviewedSnapshot, SourceSnapshotSummary } from '@/lib/api/sourceReviews';
import * as downloads from '@/lib/downloadBinary';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { report } from '@/test/fixtures.reports';

import { ReviewedSnapshots } from './ReviewedSnapshots';

const firstId = '88888888-8888-4888-8888-000000000001';
const secondId = '88888888-8888-4888-8888-000000000002';
const versionId = '66666666-6666-4666-8666-666666666666';
const summary = (id: string, subject: string): SourceSnapshotSummary => ({
  id,
  report_id: report.report.id,
  report_version_id: versionId,
  authored_by: plainUser.id,
  created_at: '2026-09-30T12:00:00Z',
  decisions: id === firstId ? 1 : 0,
  subjects: { KJ1: subject },
});
const snapshot = (id: string, subject: string): ReviewedSnapshot => ({
  id,
  report_version_id: versionId,
  authored_by: plainUser.id,
  created_at: '2026-09-30T12:00:00Z',
  projection: {
    evidence: [],
    claims: [],
    assessments: [
      {
        evidence_id: 'unmapped-capture',
        claim_id: 'unmapped-claim',
        source_id: 'bbc_world',
        subject,
        reliability: 'F',
        credibility: 6,
        source_revision: null,
        assertion_revision: null,
        authenticity: null,
      },
    ],
  },
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function renderSnapshots() {
  return render(
    <ReviewedSnapshots
      reportId={report.report.id}
      version={1}
      title="Kharkiv"
      judgements={report.version.body.key_judgements}
      canWrite
      reviewer={() => 'You'}
    />,
  );
}

describe('reviewed snapshot lifecycle', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: plainUser, status: 'authenticated' });
    vi.spyOn(reviews, 'fetchSourceSnapshots').mockResolvedValue({
      snapshots: [summary(firstId, 'ground-activity'), summary(secondId, 'maritime-activity')],
      limit: 20,
    });
    vi.spyOn(reviews, 'fetchSourceSnapshot').mockImplementation((_report, _version, id) =>
      Promise.resolve(snapshot(id, id === firstId ? 'ground-activity' : 'maritime-activity')),
    );
    vi.spyOn(downloads, 'saveBinaryFile').mockImplementation(() => undefined);
  });

  it.each(['success', 'failure'] as const)('ignores a superseded snapshot %s', async (outcome) => {
    const old = deferred<ReviewedSnapshot>();
    vi.mocked(reviews.fetchSourceSnapshot).mockImplementation((_report, _version, id) =>
      id === firstId ? old.promise : Promise.resolve(snapshot(secondId, 'maritime-activity')),
    );
    renderSnapshots();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('radio', { name: /1 reviewer decision ·/ }));
    expect(screen.getByText('Loading snapshot')).toBeVisible();
    await user.click(screen.getByRole('radio', { name: /0 reviewer decisions/ }));
    expect(await screen.findByRole('table')).toHaveTextContent('maritime-activity');
    await act(async () => {
      if (outcome === 'success') old.resolve(snapshot(firstId, 'ground-activity'));
      else old.reject(new Error('Earlier choice failed'));
      await old.promise.catch(() => undefined);
    });
    expect(screen.getByRole('table')).toHaveTextContent('maritime-activity');
    expect(screen.getByRole('table')).not.toHaveTextContent('ground-activity');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /0 reviewer decisions/ })).toBeChecked();
  });

  it.each(['success', 'failure'] as const)(
    'keeps the original assessment after a late snapshot %s',
    async (outcome) => {
      const old = deferred<ReviewedSnapshot>();
      vi.mocked(reviews.fetchSourceSnapshot).mockReturnValue(old.promise);
      renderSnapshots();
      const user = userEvent.setup();
      await user.click(await screen.findByRole('radio', { name: /1 reviewer decision ·/ }));
      await user.click(screen.getByRole('radio', { name: /Original frozen assessment/ }));
      await act(async () => {
        if (outcome === 'success') old.resolve(snapshot(firstId, 'ground-activity'));
        else old.reject(new Error('No longer accessible'));
        await old.promise.catch(() => undefined);
      });
      expect(screen.getByRole('radio', { name: /Original frozen assessment/ })).toBeChecked();
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.queryByText('Loading snapshot')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /with this snapshot/ })).not.toBeInTheDocument();
    },
  );

  it('retains subject input after creation fails and trims it on a successful retry', async () => {
    vi.spyOn(reviews, 'createSourceSnapshot')
      .mockRejectedValueOnce(new ApiError(503, 'unavailable', 'Creation unavailable'))
      .mockResolvedValueOnce(snapshot(firstId, 'ground-activity'));
    renderSnapshots();
    const user = userEvent.setup();
    const subject = await screen.findByLabelText('Subject area for KJ1');
    const create = screen.getByRole('button', { name: 'Create reviewed snapshot' });
    await user.type(subject, '   ');
    expect(create).toBeDisabled();
    await user.type(subject, 'ground-activity  ');
    await user.click(create);
    expect(await screen.findByRole('alert')).toHaveTextContent('Creation unavailable');
    expect(subject).toHaveValue('   ground-activity  ');
    await user.click(create);
    expect(await screen.findByText(/Snapshot created\. Select it/)).toBeVisible();
    expect(reviews.createSourceSnapshot).toHaveBeenNthCalledWith(2, report.report.id, 1, {
      KJ1: 'ground-activity',
    });
    expect(screen.getByRole('radio', { name: /Original frozen assessment/ })).toBeChecked();
  });

  it('identifies unmapped evidence and absent human reviews without inventing an assessment', async () => {
    const frozen = snapshot(firstId, 'ground-activity');
    frozen.projection.assessments.push({
      ...frozen.projection.assessments[0]!,
      evidence_id: 'reviewed-capture',
      authenticity: { status: 'disputed' },
      assertion_revision: { review: { id: firstId } },
    });
    vi.mocked(reviews.fetchSourceSnapshot).mockResolvedValue(frozen);
    renderSnapshots();
    await userEvent.click(await screen.findByRole('radio', { name: /1 reviewer decision ·/ }));
    const table = await screen.findByRole('table');
    expect(within(table).getByText('unmapped-capture')).toBeVisible();
    expect(within(table).getAllByText('unmapped-claim')).toHaveLength(2);
    expect(within(table).getByText('No human review: unassessed default')).toBeVisible();
    expect(within(table).getByText('Not reviewed')).toBeVisible();
    expect(within(table).getByText('Disputed')).toBeVisible();
    expect(within(table).getByText('Human review')).toBeVisible();
  });

  it('keeps a failed Word export tied to the selected snapshot for retry', async () => {
    const blob = new Blob(['document']);
    vi.spyOn(documents, 'fetchReportFile')
      .mockRejectedValueOnce(new ApiError(503, 'unavailable', 'Export unavailable'))
      .mockResolvedValueOnce(blob);
    renderSnapshots();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('radio', { name: /1 reviewer decision ·/ }));
    const download = await screen.findByRole('button', { name: 'Export Word with this snapshot' });
    await user.click(download);
    expect(await screen.findByRole('alert')).toHaveTextContent('Export unavailable');
    expect(downloads.saveBinaryFile).not.toHaveBeenCalled();
    expect(screen.getByRole('radio', { name: /1 reviewer decision ·/ })).toBeChecked();
    await user.click(download);
    await waitFor(() =>
      expect(downloads.saveBinaryFile).toHaveBeenCalledWith('kharkiv-v1-reviewed.docx', blob),
    );
    expect(documents.fetchReportFile).toHaveBeenNthCalledWith(
      2,
      report.report.id,
      1,
      'docx',
      firstId,
    );
  });

  it.each([null, 'reviewed-evidence.md'])(
    'uses the returned Markdown filename or a safe fallback (%s)',
    async (filename) => {
      const blob = new Blob(['# Reviewed assessment']);
      vi.spyOn(reports, 'fetchReportMarkdown').mockResolvedValue({ filename, blob });
      renderSnapshots();
      await userEvent.click(await screen.findByRole('radio', { name: /0 reviewer decisions/ }));
      await userEvent.click(
        await screen.findByRole('button', { name: 'Export Markdown with this snapshot' }),
      );
      await waitFor(() =>
        expect(downloads.saveBinaryFile).toHaveBeenCalledWith(
          filename ?? 'kharkiv-v1-reviewed.md',
          blob,
        ),
      );
      expect(reports.fetchReportMarkdown).toHaveBeenCalledWith(report.report.id, 1, secondId);
    },
  );
});
