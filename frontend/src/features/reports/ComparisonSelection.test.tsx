import { useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { comparisonClaim, comparisonClaimAfter } from '@/test/fixtures.comparisons';
import { identityRevision } from '@/test/fixtures.identities';
import { relationshipRevision } from '@/test/fixtures.relationships';
import { comparisonSources } from '@/test/comparisonHandlers';
import { report } from '@/test/fixtures';
import { server } from '@/test/server';
import type { ComparisonAnnotation } from './comparisonSelection';
import { ComparisonRevisionPicker } from './ComparisonRevisionPicker';
import { ComparisonCorrespondences } from './ComparisonCorrespondences';
function Picker() {
  const [selected, setSelected] = useState<ComparisonAnnotation[]>([]);
  return (
    <ComparisonRevisionPicker
      reportId={report.report.id}
      version={1}
      selected={selected}
      onChange={setSelected}
    />
  );
}
it('replaces a root selection with the chosen historical revision and recovers failed inventories', async () => {
  comparisonSources();
  let failed = true;
  server.use(
    http.get('/api/claims', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Inventory unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: [comparisonClaimAfter], total: 21, offset: 0, limit: 20 }),
    ),
  );
  render(<Picker />);
  await screen.findByRole('button', { name: 'Retry annotation inventory' });
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry annotation inventory' }));
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 2:/ }));
  await userEvent.click(screen.getByRole('button', { name: /Browse revisions/ }));
  await userEvent.click(await screen.findByRole('button', { name: 'Previous revision' }));
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 1:/ }));
  expect(screen.getByText('1 of 20 selected on this side')).toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: `Remove selected revision ${comparisonClaimAfter.id}` }),
  ).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Return to opened revision 2' }));
  await screen.findByRole('button', { name: 'Previous revision' });
  await userEvent.click(screen.getByRole('button', { name: 'Next annotation page' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Previous annotation page' })).toBeEnabled(),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Previous annotation page' }));
});
it('keeps annotation kinds separate and includes no automatic inventory selections', async () => {
  comparisonSources();
  server.use(
    http.get('/api/identity-reviews', () =>
      HttpResponse.json({ items: [identityRevision], total: 1, offset: 0, limit: 20 }),
    ),
    http.get('/api/relationship-reviews', () =>
      HttpResponse.json({ items: [relationshipRevision], total: 1, offset: 0, limit: 20 }),
    ),
  );
  render(<Picker />);
  await screen.findByRole('checkbox');
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  await userEvent.selectOptions(screen.getByLabelText('Annotation type'), 'identity');
  await userEvent.click(await screen.findByRole('checkbox'));
  await userEvent.selectOptions(screen.getByLabelText('Annotation type'), 'relationship');
  await userEvent.click(await screen.findByRole('checkbox'));
  expect(screen.getByText('2 of 20 selected on this side')).toBeInTheDocument();
  await userEvent.click(
    screen.getByRole('button', { name: `Remove selected revision ${identityRevision.id}` }),
  );
  expect(screen.getByText('1 of 20 selected on this side')).toBeInTheDocument();
});
it('requires a rationale for declared same-kind correspondence and preserves exact revision identifiers', async () => {
  const annotations = vi.fn();
  const judgements = vi.fn();
  const other = { ...comparisonClaimAfter, claim_id: 'different-root' };
  render(
    <ComparisonCorrespondences
      before={[comparisonClaim, identityRevision]}
      after={[other, relationshipRevision]}
      beforeReport={report}
      afterReport={report}
      annotations={[]}
      judgements={[]}
      onAnnotations={annotations}
      onJudgements={judgements}
    />,
  );
  await userEvent.click(screen.getByText('Optional operator-declared correspondences'));
  await userEvent.selectOptions(
    screen.getByLabelText('Annotation correspondence: selected before'),
    `claim:${comparisonClaim.id}`,
  );
  expect(screen.getByLabelText('Annotation correspondence: selected after')).not.toHaveTextContent(
    'parent',
  );
  await userEvent.selectOptions(
    screen.getByLabelText('Annotation correspondence: selected after'),
    `claim:${other.id}`,
  );
  expect(screen.getByRole('button', { name: 'Add annotation correspondence' })).toBeDisabled();
  await userEvent.type(
    screen.getByLabelText('Annotation correspondence: rationale'),
    'I intend these statements to be compared.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Add annotation correspondence' }));
  expect(annotations).toHaveBeenCalledWith([
    {
      kind: 'claim',
      before_revision_id: comparisonClaim.id,
      after_revision_id: other.id,
      rationale: 'I intend these statements to be compared.',
    },
  ]);
  await userEvent.selectOptions(
    screen.getByLabelText('Judgement correspondence: selected before'),
    'KJ1',
  );
  await userEvent.selectOptions(
    screen.getByLabelText('Judgement correspondence: selected after'),
    'KJ1',
  );
  await userEvent.type(
    screen.getByLabelText('Judgement correspondence: rationale'),
    'The question has been explicitly matched.',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Add judgement correspondence' }));
  expect(judgements).toHaveBeenCalledWith([
    {
      before_judgement_id: 'KJ1',
      after_judgement_id: 'KJ1',
      rationale: 'The question has been explicitly matched.',
    },
  ]);
});

it('enforces the combined twenty-revision cap while allowing replacement of a selected root', async () => {
  comparisonSources();
  const another = {
    ...comparisonClaimAfter,
    id: 'different-revision',
    claim_id: 'different-root',
    statement: 'Another claim',
  };
  server.use(
    http.get('/api/claims', () =>
      HttpResponse.json({ items: [comparisonClaimAfter, another], total: 2, limit: 20, offset: 0 }),
    ),
  );
  function Limited() {
    const [values, setValues] = useState<ComparisonAnnotation[]>([
      comparisonClaim,
      ...Array.from({ length: 19 }, (_, i) => ({
        ...identityRevision,
        id: `identity-revision-${i}`,
        decision_id: `identity-${i}`,
      })),
    ]);
    return (
      <ComparisonRevisionPicker
        reportId={report.report.id}
        version={1}
        selected={values}
        onChange={setValues}
      />
    );
  }
  render(<Limited />);
  const replacement = await screen.findByRole('checkbox', {
    name: /Select revision 2: Revised analytical claim/,
  });
  const extra = screen.getByRole('checkbox', { name: /Select revision 2: Another claim/ });
  expect(replacement).toBeEnabled();
  expect(extra).toBeDisabled();
  await userEvent.click(replacement);
  expect(screen.getByText('20 of 20 selected on this side')).toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: `Remove selected revision ${comparisonClaim.id}` }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole('button', { name: 'Remove selected revision identity-revision-0' }),
  );
  expect(extra).toBeEnabled();
  await userEvent.click(extra);
  expect(screen.getByText('20 of 20 selected on this side')).toBeInTheDocument();
});
it('retries an unavailable historical revision without changing the chosen root', async () => {
  comparisonSources();
  let failed = true;
  server.use(
    http.get('/api/claims/claim-1/revisions/:id', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Revision unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({
            root: {
              id: 'claim-1',
              report_id: report.report.id,
              report_version_id: 'version-1',
              report_version_number: 1,
              created_by: 'user-1',
              team_id: null,
              evidence_sha256: 'hash',
              latest_revision_id: comparisonClaimAfter.id,
              created_at: comparisonClaim.created_at,
            },
            revision: comparisonClaim,
          }),
    ),
  );
  render(<Picker />);
  await userEvent.click(await screen.findByRole('button', { name: /Browse revisions/ }));
  await screen.findByText('Revision unavailable.');
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry exact revision' }));
  await screen.findByRole('checkbox', { name: /Select revision 1:/ });
});
