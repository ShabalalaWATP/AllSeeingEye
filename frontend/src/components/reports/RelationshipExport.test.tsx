import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import {
  relationshipRevision as initial,
  relationshipRoot as root,
} from '@/test/fixtures.relationships';
import { identityRevision } from '@/test/fixtures.identities';
import { report } from '@/test/fixtures';
import { server } from '@/test/server';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import {
  ClaimExportSelection,
  IdentityExportChoice,
  RelationshipExportChoice,
} from './ClaimExportSelection';
import { RelationshipHistory } from './RelationshipHistory';
import { RelationshipFacts } from './RelationshipFacts';
import { EvidenceNavigation } from './EvidenceLinks';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
it('exports the exact selected historical assessment even after navigating to the opened revision', async () => {
  const latest = {
    ...initial,
    id: 'revision-2',
    number: 2,
    previous_id: initial.id,
    rationale: 'Updated assessment',
  };
  let posted: unknown;
  server.use(
    http.get('/api/relationship-reviews/relationship-1/revisions/:id', ({ params }) =>
      HttpResponse.json({ root, revision: params.id === initial.id ? initial : latest }),
    ),
    http.post('/api/reports/report-1/selected-evidence-package', async ({ request }) => {
      posted = await request.json();
      return new HttpResponse(new Uint8Array([80, 75]), {
        headers: { 'Content-Type': 'application/zip' },
      });
    }),
  );
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <RelationshipHistory current={latest} />
    </ClaimExportSelection>,
  );
  await userEvent.click(
    await screen.findByRole('button', { name: 'Previous relationship revision' }),
  );
  await userEvent.click(
    await screen.findByRole('checkbox', {
      name: 'Include relationship revision 1 in evidence package',
    }),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Return to opened revision 2' }));
  await screen.findByText('Updated assessment');
  await userEvent.click(screen.getByRole('button', { name: 'Download selected evidence' }));
  await waitFor(() =>
    expect(posted).toEqual({
      version_number: 1,
      revisions: [],
      relationship_revisions: [
        { relationship_id: initial.relationship_id, revision_id: initial.id },
      ],
    }),
  );
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
});
it('counts relationships with other annotation revisions under the combined twenty item cap', async () => {
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      {Array.from({ length: 20 }, (_, i) => (
        <IdentityExportChoice
          key={i}
          value={{ ...identityRevision, id: `identity-${i}`, number: i + 1 }}
        />
      ))}
      <RelationshipExportChoice value={initial} />
    </ClaimExportSelection>,
  );
  const identities = screen.getAllByRole('checkbox', { name: /Include identity revision/ });
  for (const box of identities) await userEvent.click(box);
  const relationship = screen.getByRole('checkbox', { name: /Include relationship revision/ });
  expect(relationship).toBeDisabled();
  await userEvent.click(identities[0]!);
  expect(relationship).toBeEnabled();
  await userEvent.click(relationship);
  expect(screen.getByRole('status')).toHaveTextContent('20 of 20');
  await userEvent.click(screen.getByRole('button', { name: 'Clear selection' }));
  expect(relationship).not.toBeChecked();
});
it('does not save a package after access changes while a request is pending', async () => {
  vi.mocked(saveBinaryFile).mockClear();
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  server.use(
    http.post('/api/reports/report-1/selected-evidence-package', async () => {
      started = true;
      await gate;
      return new HttpResponse(new Uint8Array([80, 75]));
    }),
  );
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <RelationshipExportChoice value={initial} />
    </ClaimExportSelection>,
  );
  await userEvent.click(screen.getByRole('checkbox'));
  await userEvent.click(screen.getByRole('button', { name: 'Download selected evidence' }));
  await waitFor(() => expect(started).toBe(true));
  await act(async () => {
    invalidateWorkspaceAccess();
    release();
    await gate;
  });
  expect(screen.getByRole('status')).toHaveTextContent('0 of 20');
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('preserves unknown periods and makes available evidence navigable without inventing dates', () => {
  const { rerender } = render(
    <EvidenceNavigation evidence={report.version.evidence}>
      <RelationshipFacts
        value={{ ...initial.assertion, periods: null, periods_state: 'missing' }}
      />
    </EvidenceNavigation>,
  );
  expect(
    screen.getByText('Period metadata is missing. Current validity is unknown.'),
  ).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'View evidence E1' })).toHaveAttribute(
    'href',
    '#evidence-E1',
  );
  rerender(
    <RelationshipFacts
      value={{
        ...initial.assertion,
        periods: [],
        periods_state: 'parsed',
        published_at: '2025-01-01T00:00:00Z',
        attributes: [],
      }}
    />,
  );
  expect(
    screen.getByText('No periods were captured. Current validity is unknown.'),
  ).toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
