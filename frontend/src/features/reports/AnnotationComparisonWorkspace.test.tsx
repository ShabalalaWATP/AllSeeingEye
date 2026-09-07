import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import type {
  AnnotationComparisonInput,
  AnnotationComparisonExportInput,
} from '@/lib/api/annotationComparisons';
import {
  annotationComparison as result,
  comparisonClaim,
  comparisonClaimAfter,
} from '@/test/fixtures.comparisons';
import { report, plainUser } from '@/test/fixtures';
import { comparisonSources } from '@/test/comparisonHandlers';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { ReportDiff } from './ReportDiff';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
async function open() {
  await userEvent.click(screen.getByText('Compare versions'));
  await userEvent.click(screen.getByRole('button', { name: 'Compare annotations and confidence' }));
  await screen.findByRole('button', { name: 'Compare exact selected inputs' });
}
it('selects a historical revision, retains exact direction and exports the preview digest', async () => {
  comparisonSources();
  let posted: AnnotationComparisonInput | undefined;
  let exported: AnnotationComparisonExportInput | undefined;
  server.use(
    http.post('/api/annotation-comparisons', async ({ request }) => {
      posted = (await request.json()) as AnnotationComparisonInput;
      return HttpResponse.json(result);
    }),
    http.post('/api/annotation-comparisons/export', async ({ request }) => {
      exported = (await request.json()) as AnnotationComparisonExportInput;
      return HttpResponse.json(result);
    }),
  );
  render(<ReportDiff id={report.report.id} current={2} latest={2} />);
  await open();
  const before = within(screen.getByRole('region', { name: 'Selected before' }));
  const after = within(screen.getByRole('region', { name: 'Selected after' }));
  await userEvent.click(await before.findByRole('button', { name: /Browse revisions/ }));
  await userEvent.click(await before.findByRole('button', { name: 'Previous revision' }));
  await userEvent.click(await before.findByRole('checkbox', { name: /Select revision 1:/ }));
  await userEvent.click(after.getByRole('checkbox', { name: /Select revision 2:/ }));
  await userEvent.click(screen.getByRole('button', { name: 'Compare exact selected inputs' }));
  await screen.findByRole('region', { name: 'Frozen annotation comparison' });
  expect(posted?.before.revisions).toEqual([
    { claim_id: comparisonClaim.claim_id, revision_id: comparisonClaim.id },
  ]);
  expect(posted?.after.revisions).toEqual([
    { claim_id: comparisonClaimAfter.claim_id, revision_id: comparisonClaimAfter.id },
  ]);
  expect(posted?.before.version_number).toBe(1);
  expect(posted?.after.version_number).toBe(2);
  await userEvent.click(screen.getByRole('button', { name: 'Export frozen comparison' }));
  await waitFor(() => expect(exported?.expected_comparison_sha256).toBe(result.comparison_sha256));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
  await userEvent.selectOptions(screen.getByLabelText('Selected before: version'), '2');
  expect(
    screen.queryByRole('region', { name: 'Frozen annotation comparison' }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: `Remove selected revision ${comparisonClaim.id}` }),
  ).not.toBeInTheDocument();
});
it('keeps exact input choices after errors and refuses a stale export without saving', async () => {
  comparisonSources();
  vi.mocked(saveBinaryFile).mockClear();
  let failed = true;
  server.use(
    http.post('/api/annotation-comparisons', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Comparison unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json(result),
    ),
    http.post('/api/annotation-comparisons/export', () =>
      HttpResponse.json(
        {
          error: {
            code: 'comparison_changed',
            message: 'Frozen comparison changed. Preview again.',
          },
        },
        { status: 409 },
      ),
    ),
  );
  render(<ReportDiff id={report.report.id} current={1} latest={1} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Compare exact selected inputs' }));
  await screen.findByText('Comparison unavailable.');
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Compare exact selected inputs' }));
  await screen.findByRole('region', { name: 'Frozen annotation comparison' });
  await userEvent.click(screen.getByRole('button', { name: 'Export frozen comparison' }));
  await screen.findByText('Frozen comparison changed. Preview again.');
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it.each(['account', 'workspace'])(
  'aborts a pending comparison and clears private results on %s change',
  async (change) => {
    comparisonSources();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    server.use(
      http.post('/api/annotation-comparisons', async () => {
        started = true;
        await gate;
        return HttpResponse.json(result);
      }),
    );
    render(<ReportDiff id={report.report.id} current={1} latest={1} />);
    await open();
    await userEvent.click(screen.getByRole('button', { name: 'Compare exact selected inputs' }));
    await waitFor(() => expect(started).toBe(true));
    await act(async () => {
      if (change === 'account') useAuthStore.setState({ user: plainUser, status: 'authenticated' });
      else invalidateWorkspaceAccess();
      release();
      await gate;
    });
    expect(
      screen.queryByRole('region', { name: 'Frozen annotation comparison' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Compare annotations and confidence' }),
    ).toHaveAttribute('aria-expanded', 'false');
  },
);
