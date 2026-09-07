import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { IdentityCreate, IdentityRevision, IdentityUpdate } from '@/lib/api/identities';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, report } from '@/test/fixtures';
import { identityRevision as initial, identityRoot } from '@/test/fixtures.identities';
import { server } from '@/test/server';
import { IdentityReviews } from './IdentityReviews';

const props = {
  reportId: 'report-1',
  version: 1,
  subject: initial.subject,
  candidates: [initial.candidate.candidate],
  evidence: report.version.evidence,
  canCreate: true,
  canManage: () => true,
};

it('recovers a failed list and allows cancellation when the current review cannot be loaded', async () => {
  sources();
  let failed = true;
  server.use(
    http.get('/api/identity-reviews', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Reviews temporarily unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: [initial], total: 1, offset: 0, limit: 20 }),
    ),
    http.get('/api/identity-reviews/identity-1', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Review detail unavailable.' } },
        { status: 503 },
      ),
    ),
    http.get('/api/identity-reviews/identity-1/revisions/:revision', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'History temporarily unavailable.' } },
        { status: 503 },
      ),
    ),
  );
  render(<IdentityReviews {...props} />);
  await userEvent.click(screen.getByRole('button', { name: 'Identity reviews and history' }));
  await screen.findByRole('button', { name: 'Retry identity reviews' });
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry identity reviews' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Review or correct identity' }));
  await screen.findByText('Review detail unavailable.');
  await userEvent.click(screen.getByRole('button', { name: 'Cancel review' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Identity revision history' }));
  await screen.findByText('History temporarily unavailable.');
});
function sources(items: IdentityRevision[] = [initial], total = items.length) {
  const offsets: string[] = [];
  server.use(
    http.get('/api/identity-reviews', ({ request }) => {
      const offset = new URL(request.url).searchParams.get('offset') ?? '0';
      offsets.push(offset);
      return HttpResponse.json({ items, total, offset: Number(offset), limit: 20 });
    }),
    http.get('/api/identity-reviews/identity-1', () =>
      HttpResponse.json({ root: identityRoot, revision: items[0] }),
    ),
    http.get('/api/identity-reviews/identity-1/revisions/:revision', ({ params }) =>
      HttpResponse.json({
        root: identityRoot,
        revision: params.revision === initial.id ? initial : items[0],
      }),
    ),
  );
  return offsets;
}
async function open() {
  await userEvent.click(screen.getByRole('button', { name: 'Identity reviews and history' }));
  await screen.findByRole('button', { name: 'Review a captured identity' });
}

it('creates a review without allowing client subject or ownership fields', async () => {
  sources([]);
  let posted: IdentityCreate | null = null;
  server.use(
    http.post('/api/identity-reviews', async ({ request }) => {
      posted = (await request.json()) as IdentityCreate;
      return HttpResponse.json(initial, { status: 201 });
    }),
  );
  render(<IdentityReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review a captured identity' }));
  expect(screen.getByText('00123456789012345678')).toBeInTheDocument();
  await userEvent.type(
    screen.getByLabelText('Decision rationale'),
    'The registration is unresolved.',
  );
  await userEvent.selectOptions(screen.getByLabelText('Identity decision'), 'matched');
  await userEvent.click(screen.getByRole('button', { name: 'Save identity review' }));
  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted).toMatchObject({
    candidate_label: 'E1',
    disposition: 'matched',
    report_id: 'report-1',
    version_number: 1,
  });
  expect(posted).not.toHaveProperty('subject');
  expect(posted).not.toHaveProperty('authored_by');
  await waitFor(() =>
    expect(screen.queryByRole('form', { name: 'Review identity' })).not.toBeInTheDocument(),
  );
});

it('retains multiline conflicts and the draft after a stale correction', async () => {
  sources();
  let posted: IdentityUpdate | null = null;
  server.use(
    http.patch('/api/identity-reviews/identity-1', async ({ request }) => {
      posted = (await request.json()) as IdentityUpdate;
      return HttpResponse.json(
        { error: { code: 'conflict', message: 'A newer revision exists.' } },
        { status: 409 },
      );
    }),
  );
  render(<IdentityReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review or correct identity' }));
  await screen.findByLabelText('Decision rationale');
  expect(screen.getByLabelText('Unresolved conflict 1')).toHaveValue('First line\nSecond line');
  await userEvent.type(
    screen.getByLabelText('Decision rationale'),
    'Check these registry differences.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save identity review' }));
  await screen.findByText(/Your draft remains here/);
  expect(screen.getByLabelText('Decision rationale')).toHaveValue(
    'Check these registry differences.',
  );
  expect(posted).toMatchObject({
    base_revision_id: initial.id,
    unresolved_conflicts: ['First line\nSecond line'],
  });
});

it('loads exact historical revisions and returns to the current review', async () => {
  const latest = {
    ...initial,
    id: 'identity-revision-2',
    number: 2,
    previous_id: initial.id,
    rationale: 'Revised rationale',
  };
  sources([latest]);
  render(<IdentityReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Identity revision history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Previous identity revision' }));
  await screen.findByText(initial.rationale);
  await userEvent.click(screen.getByRole('button', { name: 'Latest identity revision' }));
  await screen.findByRole('button', { name: 'Previous identity revision' });
});

it('explains author permissions before showing a correction form', async () => {
  sources();
  render(<IdentityReviews {...props} canManage={() => false} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review or correct identity' }));
  await screen.findByText(/Its author, a manager/);
  expect(screen.queryByLabelText('Decision rationale')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel review' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Review a captured identity' })).toBeEnabled(),
  );
});

it('prevents pagination and candidate switching from discarding an open draft', async () => {
  const offsets = sources([initial], 21);
  render(<IdentityReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review or correct identity' }));
  await userEvent.type(await screen.findByLabelText('Decision rationale'), 'Keep this draft');
  expect(screen.getByRole('button', { name: 'Next reviews' })).toBeDisabled();
  expect(screen.getByLabelText('Captured candidate')).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Next reviews' }));
  expect(offsets).toEqual(['0']);
  expect(screen.getByLabelText('Decision rationale')).toHaveValue('Keep this draft');
  await userEvent.click(screen.getByRole('button', { name: 'Cancel review' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Next reviews' })).toBeEnabled());
});

it.each(['account', 'access', 'report', 'version'])(
  'clears private drafts on %s changes',
  async (change) => {
    sources([]);
    const view = render(<IdentityReviews {...props} />);
    await open();
    await userEvent.click(screen.getByRole('button', { name: 'Review a captured identity' }));
    await userEvent.type(screen.getByLabelText('Decision rationale'), 'Private draft');
    if (change === 'account')
      act(() => {
        useAuthStore.setState({ user: plainUser, status: 'authenticated' });
      });
    else if (change === 'access')
      act(() => {
        invalidateWorkspaceAccess();
      });
    else
      view.rerender(
        <IdentityReviews
          {...props}
          reportId={change === 'report' ? 'another' : props.reportId}
          version={change === 'version' ? 2 : 1}
        />,
      );
    expect(screen.queryByLabelText('Decision rationale')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Identity reviews and history' })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  },
);

it('paginates reviews and explains reports without an explicit company subject', async () => {
  const offsets = sources([initial], 21);
  render(<IdentityReviews {...props} subject={null} />);
  await userEvent.click(screen.getByRole('button', { name: 'Identity reviews and history' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Next reviews' }));
  await waitFor(() => expect(offsets).toContain('20'));
  await userEvent.click(screen.getByRole('button', { name: 'Previous reviews' }));
  await waitFor(() => expect(offsets.at(-1)).toBe('0'));
  expect(screen.getByText(/explicit company research subject/)).toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'Review a captured identity' }),
  ).not.toBeInTheDocument();
});
