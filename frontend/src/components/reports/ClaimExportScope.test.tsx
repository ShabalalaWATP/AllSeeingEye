import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import type { ClaimRevision } from '@/lib/api/claims';
import { ClaimExportChoice, ClaimExportSelection } from './ClaimExportSelection';

function revision(number: number): ClaimRevision {
  return {
    id: `revision-${String(number)}`,
    claim_id: 'claim-1',
    report_id: 'report-1',
    report_version_id: 'version-1',
    number,
    previous_id: null,
    statement: `Assertion ${String(number)}`,
    kind: 'reported_fact',
    state: 'proposed',
    citations: [],
    unresolved_conflicts: [],
    reason: 'Fixture',
    model_origin: null,
    authored_by: 'user-1',
    created_at: '2026-09-07T00:00:00Z',
  };
}

it('bounds selection to 20 and releases capacity when one revision is removed', async () => {
  render(
    <ClaimExportSelection reportId="report-1" version={1}>
      {Array.from({ length: 21 }, (_, i) => (
        <ClaimExportChoice key={i} value={revision(i + 1)} />
      ))}
    </ClaimExportSelection>,
  );
  const user = userEvent.setup();
  for (let i = 1; i <= 20; i++)
    await user.click(screen.getByLabelText(`Include revision ${String(i)} in evidence package`));
  expect(screen.getByText('20 of 20 revisions selected')).toBeInTheDocument();
  expect(screen.getByLabelText('Include revision 21 in evidence package')).toBeDisabled();
  await user.click(screen.getByLabelText('Include revision 1 in evidence package'));
  expect(screen.getByLabelText('Include revision 21 in evidence package')).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Clear selection' }));
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
});

it.each(['report', 'version'])('clears selection when the %s changes', async (change) => {
  const view = render(
    <ClaimExportSelection reportId="report-1" version={1}>
      <ClaimExportChoice value={revision(1)} />
    </ClaimExportSelection>,
  );
  await userEvent.click(screen.getByLabelText('Include revision 1 in evidence package'));
  view.rerender(
    <ClaimExportSelection
      reportId={change === 'report' ? 'report-2' : 'report-1'}
      version={change === 'version' ? 2 : 1}
    >
      <ClaimExportChoice value={revision(1)} />
    </ClaimExportSelection>,
  );
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
  expect(screen.getByLabelText('Include revision 1 in evidence package')).not.toBeChecked();
});
