import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type {
  RelationshipCreate,
  RelationshipRevision,
  RelationshipUpdate,
} from '@/lib/api/relationships';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { report } from '@/test/fixtures';
import {
  relationshipRevision as initial,
  relationshipRoot as root,
} from '@/test/fixtures.relationships';
import { server } from '@/test/server';
import { RelationshipReviews } from './RelationshipReviews';
const props = {
  reportId: 'report-1',
  version: 1,
  evidence: report.version.evidence,
  canCreate: true,
  canManage: () => true,
};
function sources(items: RelationshipRevision[] = [initial]) {
  server.use(
    http.get('/api/relationship-reviews/assertions', () =>
      HttpResponse.json({ items: [initial.assertion], unavailable_labels: [], review_ids: {} }),
    ),
    http.get('/api/relationship-reviews', () =>
      HttpResponse.json({ items, total: items.length, offset: 0, limit: 20 }),
    ),
    http.get('/api/relationship-reviews/relationship-1', () =>
      HttpResponse.json({ root, revision: items[0] }),
    ),
  );
}
async function open() {
  await userEvent.click(screen.getByRole('button', { name: 'Relationship reviews and history' }));
  await screen.findByRole('button', { name: 'Review a captured relationship' });
}
it('uses server assertions to create an attributed assessment without mutable source or ownership fields', async () => {
  sources([]);
  let body: RelationshipCreate | undefined;
  server.use(
    http.post('/api/relationship-reviews', async ({ request }) => {
      body = (await request.json()) as RelationshipCreate;
      return HttpResponse.json(initial, { status: 201 });
    }),
  );
  render(<RelationshipReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review a captured relationship' }));
  expect(
    screen.getByText(/Source-reported direct accounting-consolidation parent/),
  ).toBeInTheDocument();
  expect(screen.getByText(/2020-01-01 to 2020-12-31/)).toBeInTheDocument();
  expect(screen.queryByRole('option', { name: 'Withdrawn', hidden: true })).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Relationship assessment'), 'supported');
  await userEvent.type(
    screen.getByLabelText('Assessment rationale'),
    'The accounting record supports this historical relationship.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Add unresolved conflict' }));
  await userEvent.type(
    screen.getByLabelText('Unresolved conflict 1'),
    'The end date needs checking.',
  );
  const excerpt = screen.getByLabelText<HTMLTextAreaElement>('Select the exact excerpt');
  act(() => {
    excerpt.setSelectionRange(0, 4);
    fireEvent.select(excerpt);
  });
  await userEvent.selectOptions(screen.getByLabelText('Evidence relationship'), 'context');
  await userEvent.click(screen.getByRole('button', { name: 'Add selected excerpt' }));
  await userEvent.click(screen.getByRole('button', { name: 'Save relationship review' }));
  await waitFor(() =>
    expect(body).toMatchObject({
      evidence_label: 'E1',
      disposition: 'supported',
      report_id: 'report-1',
      version_number: 1,
    }),
  );
  expect(body?.citations).toEqual([
    {
      label: 'E1',
      relation: 'context',
      field: 'title',
      start: 0,
      end: 4,
      text: report.version.evidence[0]!.title.slice(0, 4),
    },
  ]);
  expect(body?.unresolved_conflicts).toEqual(['The end date needs checking.']);
  expect(body).not.toHaveProperty('assertion');
  expect(body).not.toHaveProperty('subject');
  expect(body).not.toHaveProperty('ownership');
});
it('keeps conflict drafts until explicit reload and submits the fresh revision after reloading', async () => {
  sources();
  let latest = initial;
  const sent: RelationshipUpdate[] = [];
  server.use(
    http.get('/api/relationship-reviews/relationship-1', () =>
      HttpResponse.json({ root, revision: latest }),
    ),
    http.patch('/api/relationship-reviews/relationship-1', async ({ request }) => {
      sent.push((await request.json()) as RelationshipUpdate);
      if (sent.length === 1) {
        latest = { ...initial, id: 'revision-2', number: 2, previous_id: initial.id };
        return HttpResponse.json(
          { error: { code: 'revision_conflict', message: 'Another assessment was saved.' } },
          { status: 409 },
        );
      }
      return HttpResponse.json({ ...latest, id: 'revision-3', number: 3 });
    }),
  );
  render(<RelationshipReviews {...props} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review or correct relationship' }));
  await userEvent.type(
    await screen.findByLabelText('Assessment rationale'),
    'Private correction draft',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save relationship review' }));
  await screen.findByText(/Another assessment was saved/);
  expect(screen.getByLabelText('Assessment rationale')).toHaveValue('Private correction draft');
  await userEvent.click(screen.getByRole('button', { name: 'Discard draft and reload review' }));
  await waitFor(() => expect(screen.getByLabelText('Assessment rationale')).toHaveValue(''));
  await userEvent.selectOptions(screen.getByLabelText('Relationship assessment'), 'disputed');
  await userEvent.type(
    screen.getByLabelText('Assessment rationale'),
    'A fresh counter-source disputes the period.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save relationship review' }));
  await waitFor(() => expect(sent).toHaveLength(2));
  expect(sent[0]?.base_revision_id).toBe(initial.id);
  expect(sent[1]?.base_revision_id).toBe('revision-2');
});
it('uses no client fallback when source projection is unavailable and still permits reading existing reviews', async () => {
  sources();
  server.use(
    http.get('/api/relationship-reviews/assertions', () =>
      HttpResponse.json({ items: [], unavailable_labels: ['E1'], review_ids: {} }),
    ),
  );
  render(<RelationshipReviews {...props} />);
  await userEvent.click(screen.getByRole('button', { name: 'Relationship reviews and history' }));
  await screen.findByText(/Legacy or incomplete records/);
  expect(
    screen.queryByRole('button', { name: 'Review a captured relationship' }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(initial.rationale)).toBeInTheDocument();
});
it('checks current permissions before exposing a correction draft and clears private drafts on version or access changes', async () => {
  sources();
  const view = render(<RelationshipReviews {...props} canManage={() => false} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review or correct relationship' }));
  await screen.findByText(/Its author/);
  expect(screen.queryByLabelText('Assessment rationale')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel review' }));
  await userEvent.click(
    await screen.findByRole('button', { name: 'Review a captured relationship' }),
  );
  await userEvent.type(screen.getByLabelText('Assessment rationale'), 'Private');
  view.rerender(<RelationshipReviews {...props} version={2} />);
  expect(screen.queryByLabelText('Assessment rationale')).not.toBeInTheDocument();
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Review a captured relationship' }));
  expect(screen.getByLabelText('Assessment rationale')).toHaveValue('');
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
});
it('recovers a failed list and history request without claiming a history revision is current', async () => {
  sources();
  let failed = true;
  server.use(
    http.get('/api/relationship-reviews', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Try again.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: [initial], total: 1, offset: 0, limit: 20 }),
    ),
    http.get('/api/relationship-reviews/relationship-1/revisions/:id', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'History unavailable.' } },
        { status: 503 },
      ),
    ),
  );
  render(<RelationshipReviews {...props} />);
  await userEvent.click(screen.getByRole('button', { name: 'Relationship reviews and history' }));
  await screen.findByRole('button', { name: 'Retry relationship reviews' });
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry relationship reviews' }));
  await userEvent.click(
    await screen.findByRole('button', { name: 'Relationship revision history' }),
  );
  expect(
    await screen.findByRole('button', { name: 'Retry relationship revision' }),
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole('region', { name: 'Relationship reviews' })).queryByText(
      /Latest relationship revision/,
    ),
  ).not.toBeInTheDocument();
});

it('opens an existing review from the server mapping when it is beyond the current page', async () => {
  sources([]);
  const beyond = { ...initial, id: 'beyond-revision', relationship_id: 'beyond-page', number: 4 };
  let created = false;
  server.use(
    http.get('/api/relationship-reviews/assertions', () =>
      HttpResponse.json({
        items: [initial.assertion],
        unavailable_labels: [],
        review_ids: { E1: 'beyond-page' },
      }),
    ),
    http.get('/api/relationship-reviews', () =>
      HttpResponse.json({ items: [], total: 21, offset: 0, limit: 20 }),
    ),
    http.get('/api/relationship-reviews/beyond-page', () =>
      HttpResponse.json({
        root: { ...root, id: 'beyond-page', latest_revision_id: beyond.id },
        revision: beyond,
      }),
    ),
    http.post('/api/relationship-reviews', () => {
      created = true;
      return HttpResponse.json(initial);
    }),
  );
  render(<RelationshipReviews {...props} />);
  await userEvent.click(screen.getByRole('button', { name: 'Relationship reviews and history' }));
  await userEvent.click(
    await screen.findByRole('button', { name: 'Open existing relationship review' }),
  );
  await screen.findByRole('form', { name: 'Correct relationship review' });
  expect(screen.getByRole('option', { name: 'Withdrawn' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Next reviews' })).toBeDisabled();
  expect(created).toBe(false);
});
