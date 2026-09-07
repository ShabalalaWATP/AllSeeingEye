import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { ClaimRevision } from '@/lib/api/claims';
import { report } from '@/test/fixtures';
import { server } from '@/test/server';
import { ClaimAnnotations } from './ClaimAnnotations';

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
  report_version_number: 1,
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

function sources(total = 1) {
  let current = revised;
  const offsets: string[] = [];
  server.use(
    http.get('/api/claims', ({ request }) => {
      const offset = new URL(request.url).searchParams.get('offset') ?? '0';
      offsets.push(offset);
      return HttpResponse.json({ items: [current], total, limit: 20, offset: Number(offset) });
    }),
    http.get('/api/claims/claim-1', () => HttpResponse.json({ root, revision: current })),
    http.get('/api/claims/claim-1/revisions/:revision', ({ params }) =>
      HttpResponse.json({ root, revision: params.revision === initial.id ? initial : current }),
    ),
    http.patch('/api/claims/claim-1', async ({ request }) => {
      const body = (await request.json()) as Partial<ClaimRevision>;
      current = {
        ...current,
        ...body,
        citations: current.citations,
        id: 'revision-3',
        number: 3,
        previous_id: 'revision-2',
      };
      return HttpResponse.json(current);
    }),
  );
  return offsets;
}

it('navigates exact older revisions and bounded pages', async () => {
  const offsets = sources(21);
  render(<ClaimAnnotations reportId="report-1" version={1} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  expect(await screen.findByText('Model proposal provenance')).toBeInTheDocument();
  expect(screen.getByText('configured-model')).toBeInTheDocument();
  await user.click(await screen.findByRole('button', { name: 'Revision history' }));
  await user.click(await screen.findByRole('button', { name: 'Previous revision' }));
  expect(await screen.findByText('Original assertion')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Latest revision' }));
  await waitFor(() => expect(screen.queryByText('Original assertion')).not.toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: 'Next page' }));
  await waitFor(() => expect(offsets).toContain('20'));
  await user.click(screen.getByRole('button', { name: 'Previous page' }));
  await waitFor(() => expect(offsets.at(-1)).toBe('0'));
});

it('loads current permissions and saves an appended review through the API', async () => {
  sources();
  render(
    <ClaimAnnotations
      reportId="report-1"
      version={1}
      evidence={report.version.evidence}
      canCreate
      canManage={() => true}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByRole('button', { name: 'Review or correct claim' }));
  const form = await screen.findByRole('form', { name: 'Revise claim' });
  await user.selectOptions(within(form).getByLabelText('Review state'), 'reviewed');
  await user.type(
    within(form).getByLabelText('Reason for this revision'),
    'Reviewed the original source.',
  );
  await user.click(within(form).getByRole('button', { name: 'Save new revision' }));
  await waitFor(() =>
    expect(screen.queryByRole('form', { name: 'Revise claim' })).not.toBeInTheDocument(),
  );
  expect(
    await screen.findByText(/Revision reason: Reviewed the original source/),
  ).toBeInTheDocument();
});

it('withholds editing when the current root permissions deny it', async () => {
  sources();
  render(<ClaimAnnotations reportId="report-1" version={1} canCreate canManage={() => false} />);
  await userEvent.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Review or correct claim' }));
  expect(
    await screen.findByText('You can read this claim, but cannot revise it.'),
  ).toBeInTheDocument();
  expect(screen.queryByRole('form', { name: 'Revise claim' })).not.toBeInTheDocument();
});

it('shows a revision-load failure without displaying an editor', async () => {
  sources();
  server.use(http.get('/api/claims/claim-1', () => HttpResponse.json({}, { status: 500 })));
  render(<ClaimAnnotations reportId="report-1" version={1} canCreate canManage={() => true} />);
  await userEvent.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Review or correct claim' }));
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  expect(screen.queryByRole('form', { name: 'Revise claim' })).not.toBeInTheDocument();
});
