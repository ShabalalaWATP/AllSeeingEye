import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import type { ClaimRevision } from '@/lib/api/claims';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { identityRevision as initial, identityRoot } from '@/test/fixtures.identities';
import { server } from '@/test/server';
import {
  ClaimExportChoice,
  ClaimExportSelection,
  IdentityExportChoice,
} from './ClaimExportSelection';
import { IdentityReviews } from './IdentityReviews';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

const claim: ClaimRevision = {
  id: initial.id,
  claim_id: 'claim-1',
  report_id: initial.report_id,
  report_version_id: initial.report_version_id,
  number: 1,
  previous_id: null,
  statement: 'Captured registry assertion',
  kind: 'reported_fact',
  state: 'proposed',
  citations: [],
  unresolved_conflicts: [],
  reason: 'Captured',
  model_origin: null,
  authored_by: initial.authored_by,
  created_at: initial.created_at,
};

it('exports a claim and an explicitly chosen earlier identity review from one tray', async () => {
  vi.mocked(saveBinaryFile).mockClear();
  const latest = { ...initial, id: 'identity-revision-2', number: 2, previous_id: initial.id };
  let body: unknown;
  server.use(
    http.get('/api/identity-reviews', () =>
      HttpResponse.json({ items: [latest], total: 1, offset: 0, limit: 20 }),
    ),
    http.get('/api/identity-reviews/identity-1/revisions/:revision', ({ params }) =>
      HttpResponse.json({
        root: identityRoot,
        revision: params.revision === initial.id ? initial : latest,
      }),
    ),
    http.post('/api/reports/report-1/selected-evidence-package', async ({ request }) => {
      body = await request.json();
      return new HttpResponse('fixture zip');
    }),
  );
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <ClaimExportChoice value={claim} />
      <IdentityReviews
        reportId="report-1"
        version={1}
        subject={initial.subject}
        candidates={[initial.candidate.candidate]}
        evidence={[]}
        canCreate={false}
        canManage={() => false}
      />
    </ClaimExportSelection>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByLabelText('Include revision 1 in evidence package'));
  await user.click(screen.getByRole('button', { name: 'Identity reviews and history' }));
  await user.click(await screen.findByRole('button', { name: 'Identity revision history' }));
  await user.click(await screen.findByRole('button', { name: 'Previous identity revision' }));
  await user.click(await screen.findByLabelText('Include identity revision 1 in evidence package'));
  expect(screen.getByText('2 of 20 revisions selected')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Identity reviews and history' }));
  await user.click(screen.getByRole('button', { name: 'Download selected evidence' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalledOnce());
  expect(body).toEqual({
    version_number: 1,
    revisions: [{ claim_id: claim.claim_id, revision_id: claim.id }],
    identity_revisions: [{ decision_id: initial.decision_id, revision_id: initial.id }],
  });
  expect(saveBinaryFile).toHaveBeenCalledWith(
    'report-v1-selected-annotations.zip',
    expect.objectContaining({ size: 11, type: 'text/plain;charset=utf-8' }),
  );
});

it('applies one combined cap and removes identity selections without changing claims', async () => {
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <ClaimExportChoice value={claim} />
      {Array.from({ length: 20 }, (_, i) => (
        <IdentityExportChoice key={i} value={{ ...initial, id: `identity-${i}`, number: i + 1 }} />
      ))}
    </ClaimExportSelection>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByLabelText('Include revision 1 in evidence package'));
  for (let i = 1; i <= 19; i++)
    await user.click(screen.getByLabelText(`Include identity revision ${i} in evidence package`));
  expect(screen.getByLabelText('Include identity revision 20 in evidence package')).toBeDisabled();
  await user.click(
    screen.getByRole('button', {
      name: `Remove identity revision 1: ${initial.subject} · Candidate E1`,
    }),
  );
  expect(screen.getByLabelText('Include identity revision 20 in evidence package')).toBeEnabled();
  expect(screen.getByLabelText('Include revision 1 in evidence package')).toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Clear selection' }));
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
});

it('aborts an identity-only download and clears its selection when access changes', async () => {
  vi.mocked(saveBinaryFile).mockClear();
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let started = false;
  server.use(
    http.post('/api/reports/report-1/selected-evidence-package', async () => {
      started = true;
      await pending;
      return new HttpResponse('fixture zip');
    }),
  );
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <IdentityExportChoice value={initial} />
    </ClaimExportSelection>,
  );
  await userEvent.click(screen.getByLabelText('Include identity revision 1 in evidence package'));
  await userEvent.click(screen.getByRole('button', { name: 'Download selected evidence' }));
  await waitFor(() => expect(started).toBe(true));
  act(() => {
    invalidateWorkspaceAccess();
  });
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
