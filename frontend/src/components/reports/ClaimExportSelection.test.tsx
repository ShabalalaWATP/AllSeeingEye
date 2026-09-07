import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import type { ClaimRevision } from '@/lib/api/claims';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { ClaimAnnotations } from './ClaimAnnotations';
import { useAuthStore } from '@/stores/auth';
import { plainUser, adminUser, tokenFor } from '@/test/fixtures';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
const initial: ClaimRevision = {
  model_origin: {
    batch_id: 'batch-1',
    profile_id: 'profile-1',
    profile_revision: 2,
    provider: 'openai_compatible',
    requested_model: 'configured-model',
    returned_model: 'returned-model',
    input_sha256: 'a'.repeat(64),
    method_version: 'ase-claim-proposals-v1',
    generated_at: '2026-09-07T00:00:00Z',
  },
  id: 'revision-1',
  claim_id: 'claim-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  number: 1,
  previous_id: null,
  statement: 'Original assertion',
  kind: 'analytical_inference',
  state: 'proposed',
  citations: [
    {
      label: 'E1',
      relation: 'supporting',
      event_id: 'event-1',
      source_content_hash: 'hash',
      excerpt: { field: 'title', start: 0, end: 4, text: 'Text', sha256: 'hash' },
    },
  ],
  unresolved_conflicts: ['Date remains unknown.'],
  reason: 'Initial capture',
  authored_by: 'user-1',
  created_at: '2026-09-07T00:00:00Z',
};
const root = {
  id: 'claim-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  report_version_number: 3,
  created_by: 'user-1',
  team_id: null,
  evidence_sha256: 'hash',
  latest_revision_id: 'revision-2',
  created_at: initial.created_at,
};
const revised = {
  ...initial,
  id: 'revision-2',
  previous_id: initial.id,
  number: 2,
  statement: 'Revised assertion',
};

function setup() {
  vi.mocked(saveBinaryFile).mockClear();
  server.use(
    http.get('/api/claims', () =>
      HttpResponse.json({ items: [revised], total: 1, limit: 20, offset: 0 }),
    ),
    http.get('/api/claims/claim-1/revisions/:revision', ({ params }) =>
      HttpResponse.json({ root, revision: params.revision === initial.id ? initial : revised }),
    ),
  );
  return render(<ClaimAnnotations reportId="report-1" version={3} />);
}
it('exports an explicitly selected historical revision', async () => {
  let body: unknown;
  server.use(
    http.post('/api/reports/report-1/claim-evidence-package', async ({ request }) => {
      body = await request.json();
      return new HttpResponse('fixture zip');
    }),
  );
  setup();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByRole('button', { name: 'Revision history' }));
  await user.click(await screen.findByRole('button', { name: 'Previous revision' }));
  await user.click(await screen.findByLabelText('Include revision 1 in evidence package'));
  await user.click(screen.getByRole('button', { name: 'Download selected claims' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalledOnce());
  expect(body).toEqual({
    version_number: 3,
    revisions: [{ claim_id: 'claim-1', revision_id: 'revision-1' }],
  });
});
it.each(['access', 'account'])(
  'clears selection and suppresses pending download after %s changes',
  async (change) => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    let finish: (() => void) | undefined;
    const pending = new Promise<void>((resolve) => {
      finish = resolve;
    });
    let started = false;
    server.use(
      http.post('/api/reports/report-1/claim-evidence-package', async () => {
        started = true;
        await pending;
        return new HttpResponse('fixture zip');
      }),
    );
    setup();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
    await user.click(await screen.findByLabelText('Include revision 2 in evidence package'));
    await user.click(screen.getByRole('button', { name: 'Download selected claims' }));
    await waitFor(() => expect(started).toBe(true));
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
    await act(async () => {
      finish?.();
      await pending;
    });
    expect(saveBinaryFile).not.toHaveBeenCalled();
  },
);

it('retains exact selections across pages and sends both selected identities', async () => {
  setup();
  const another = {
    ...initial,
    id: 'revision-other',
    claim_id: 'claim-other',
    statement: 'Other assertion',
  };
  let submitted: unknown;
  server.use(
    http.get('/api/claims', ({ request }) => {
      const offset = Number(new URL(request.url).searchParams.get('offset'));
      return HttpResponse.json({
        items: offset === 0 ? [revised] : [another],
        total: 21,
        limit: 20,
        offset,
      });
    }),
    http.post('/api/reports/report-1/claim-evidence-package', async ({ request }) => {
      submitted = await request.json();
      return new HttpResponse('fixture zip');
    }),
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByLabelText('Include revision 2 in evidence package'));
  await user.click(screen.getByRole('button', { name: 'Next page' }));
  await user.click(await screen.findByLabelText('Include revision 1 in evidence package'));
  expect(screen.getByText('2 of 20 revisions selected')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Download selected claims' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalledOnce());
  expect(submitted).toEqual({
    version_number: 3,
    revisions: [
      { claim_id: 'claim-1', revision_id: 'revision-2' },
      { claim_id: 'claim-other', revision_id: 'revision-other' },
    ],
  });
});
it('retains selection on download failure and permits removal', async () => {
  server.use(
    http.post('/api/reports/report-1/claim-evidence-package', () =>
      HttpResponse.json(
        { error: { code: 'conflict', message: 'Report changed. Retry the export.' } },
        { status: 409 },
      ),
    ),
  );
  setup();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByLabelText('Include revision 2 in evidence package'));
  await user.click(screen.getByRole('button', { name: 'Download selected claims' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Report changed');
  expect(screen.getByText('1 of 20 revisions selected')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Remove revision 2: Revised assertion' }));
  expect(screen.getByRole('button', { name: 'Download selected claims' })).toBeDisabled();
});
