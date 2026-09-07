import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import type { ClaimRevision } from '@/lib/api/claims';
import { RevisionText } from '@/components/reports/ClaimHistory';
import { IdentityRevisionText } from '@/components/reports/IdentityHistory';
import { identityRevision } from '@/test/fixtures.identities';
import { report } from '@/test/fixtures';
import { EvidenceNavigation, evidenceId } from './EvidenceLinks';

const citation: ClaimRevision['citations'][number] = {
  label: 'E1',
  relation: 'supporting',
  event_id: 'event-1',
  source_content_hash: 'hash',
  excerpt: { field: 'title', start: 0, end: 4, text: 'Text', sha256: 'hash' },
};
const claim: ClaimRevision = {
  id: 'revision-1',
  claim_id: 'claim-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  number: 1,
  previous_id: null,
  statement: 'Original assertion',
  kind: 'reported_fact',
  state: 'proposed',
  citations: [citation],
  unresolved_conflicts: [],
  reason: 'Initial capture',
  authored_by: 'user-1',
  created_at: '2026-09-07T00:00:00Z',
  model_origin: null,
};

it.each(['claim', 'identity'] as const)(
  'opens the exact annex from a historical %s citation',
  async (kind) => {
    const user = userEvent.setup();
    render(
      <EvidenceNavigation evidence={report.version.evidence}>
        {kind === 'claim' ? (
          <RevisionText value={claim} />
        ) : (
          <IdentityRevisionText value={{ ...identityRevision, citations: [citation] }} />
        )}
        <details id={evidenceId('E1')} data-testid="annex">
          <summary>Captured evidence E1</summary>
          <p>Original source record</p>
        </details>
      </EvidenceNavigation>,
    );
    const link = screen.getByRole('link', { name: 'View evidence E1' });
    link.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('annex')).toHaveAttribute('open');
    expect(screen.getByText('Captured evidence E1')).toHaveFocus();
    expect(screen.getByText('Text')).toBeInTheDocument();
    expect(screen.getByText(/supporting · Original title/)).toBeInTheDocument();
  },
);

it('keeps an unavailable citation as inert text in the selected version', () => {
  render(
    <EvidenceNavigation evidence={[]}>
      <RevisionText value={claim} />
    </EvidenceNavigation>,
  );
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  const quote = screen.getByText('Text').closest('blockquote');
  expect(within(quote!).getByText('E1')).toBeInTheDocument();
});
