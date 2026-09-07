import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures';
import {
  annotationComparison as result,
  comparisonClaim,
  comparisonClaimAfter,
} from '@/test/fixtures.comparisons';
import { comparisonSources } from '@/test/comparisonHandlers';
import { server } from '@/test/server';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import type { AnnotationComparisonInput } from '@/lib/api/annotationComparisons';
import { ReportDiff } from './ReportDiff';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
async function open() {
  await userEvent.click(screen.getByText('Compare versions'));
  await userEvent.click(screen.getByRole('button', { name: 'Compare annotations and confidence' }));
}
it('does not save a completed export after permission loss or unmount', async () => {
  comparisonSources();
  vi.mocked(saveBinaryFile).mockClear();
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  server.use(
    http.post('/api/annotation-comparisons', () => HttpResponse.json(result)),
    http.post('/api/annotation-comparisons/export', async () => {
      started = true;
      await gate;
      return HttpResponse.json(result);
    }),
  );
  const view = render(<ReportDiff id={report.report.id} current={1} latest={1} />);
  await open();
  await userEvent.click(
    await screen.findByRole('button', { name: 'Compare exact selected inputs' }),
  );
  await userEvent.click(await screen.findByRole('button', { name: 'Export frozen comparison' }));
  await waitFor(() => expect(started).toBe(true));
  await act(async () => {
    invalidateWorkspaceAccess();
    view.unmount();
    release();
    await gate;
  });
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('preserves explicit operator correspondence in the actual comparison request', async () => {
  comparisonSources();
  const other = { ...comparisonClaimAfter, claim_id: 'another-root' };
  let body: AnnotationComparisonInput | undefined;
  server.use(
    http.get('/api/claims', ({ request }) =>
      HttpResponse.json({
        items: [
          new URL(request.url).searchParams.get('version_number') === '1' ? comparisonClaim : other,
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }),
    ),
    http.post('/api/annotation-comparisons', async ({ request }) => {
      body = (await request.json()) as AnnotationComparisonInput;
      return HttpResponse.json(result);
    }),
  );
  render(<ReportDiff id={report.report.id} current={2} latest={2} />);
  await open();
  await userEvent.click(
    await within(screen.getByRole('region', { name: 'Selected before' })).findByRole('checkbox'),
  );
  await userEvent.click(
    within(screen.getByRole('region', { name: 'Selected after' })).getByRole('checkbox'),
  );
  await userEvent.click(screen.getByText('Optional operator-declared correspondences'));
  await userEvent.selectOptions(
    screen.getByLabelText('Annotation correspondence: selected before'),
    `claim:${comparisonClaim.id}`,
  );
  await userEvent.selectOptions(
    screen.getByLabelText('Annotation correspondence: selected after'),
    `claim:${other.id}`,
  );
  await userEvent.type(
    screen.getByLabelText('Annotation correspondence: rationale'),
    'These two reviewed claims address the same question.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Add annotation correspondence' }));
  await userEvent.click(screen.getByRole('button', { name: 'Compare exact selected inputs' }));
  await waitFor(() =>
    expect(body?.correspondences).toEqual([
      {
        kind: 'claim',
        before_revision_id: comparisonClaim.id,
        after_revision_id: other.id,
        rationale: 'These two reviewed claims address the same question.',
      },
    ]),
  );
});
it('recovers unavailable report inputs without exposing a stale result', async () => {
  comparisonSources();
  let fail = true;
  server.use(
    http.get('/api/reports/:id', () =>
      fail
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Report inputs unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json(report),
    ),
  );
  render(<ReportDiff id={report.report.id} current={1} latest={1} />);
  await open();
  await screen.findByText('Report inputs unavailable.');
  expect(
    screen.queryByRole('button', { name: 'Compare exact selected inputs' }),
  ).not.toBeInTheDocument();
  fail = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry comparison inputs' }));
  await screen.findByRole('button', { name: 'Compare exact selected inputs' });
});
