import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import type { IdentityUpdate } from '@/lib/api/identities';
import { report } from '@/test/fixtures';
import { identityRevision } from '@/test/fixtures.identities';
import { server } from '@/test/server';
import { IdentityEditor } from './IdentityEditor';

it('allows explicit conflict removal, replacement and withdrawal without rewriting previous history', async () => {
  let posted: IdentityUpdate | null = null;
  const saved = vi.fn();
  const current = {
    ...identityRevision,
    citations: [
      {
        label: 'E1',
        relation: 'supporting' as const,
        event_id: 'event-1',
        source_content_hash: 'hash',
        excerpt: { field: 'title' as const, start: 0, end: 4, text: 'Text', sha256: 'hash' },
      },
    ],
  };
  server.use(
    http.patch('/api/identity-reviews/identity-1', async ({ request }) => {
      posted = (await request.json()) as IdentityUpdate;
      return HttpResponse.json({
        ...current,
        id: 'revision-2',
        previous_id: current.id,
        number: 2,
      });
    }),
  );
  render(
    <IdentityEditor
      reportId="report-1"
      version={1}
      label="E1"
      subject={current.subject}
      evidence={report.version.evidence}
      current={current}
      onSaved={saved}
      onCancel={vi.fn()}
    />,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Remove conflict 1' }));
  await userEvent.click(screen.getByRole('button', { name: 'Add unresolved conflict' }));
  await userEvent.type(
    screen.getByLabelText('Unresolved conflict 1'),
    'A different registry issue',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Remove excerpt 1' }));
  await userEvent.selectOptions(screen.getByLabelText('Identity decision'), 'withdrawn');
  await userEvent.type(
    screen.getByLabelText('Decision rationale'),
    'Withdraw pending more evidence.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save identity review' }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(posted).toMatchObject({
    disposition: 'withdrawn',
    citations: [],
    unresolved_conflicts: ['A different registry issue'],
    base_revision_id: current.id,
  });
  expect(current.unresolved_conflicts).toEqual(['First line\nSecond line']);
  expect(current.citations[0]?.excerpt.text).toBe('Text');
});

it('adds exact excerpts once and supports cancelling a new review', async () => {
  const cancel = vi.fn();
  render(
    <IdentityEditor
      reportId="report-1"
      version={1}
      label="E1"
      subject={identityRevision.subject}
      evidence={report.version.evidence}
      onSaved={vi.fn()}
      onCancel={cancel}
    />,
  );
  expect(screen.queryByRole('option', { name: 'Withdrawn' })).not.toBeInTheDocument();
  const text = screen.getByLabelText<HTMLTextAreaElement>('Select the exact excerpt');
  text.focus();
  text.setSelectionRange(0, 4);
  fireEvent.select(text);
  await userEvent.click(screen.getByRole('button', { name: 'Add selected excerpt' }));
  await userEvent.click(screen.getByRole('button', { name: 'Add selected excerpt' }));
  expect(screen.getByRole('button', { name: 'Remove excerpt 1' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Remove excerpt 2' })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel review' }));
  expect(cancel).toHaveBeenCalledOnce();
});
