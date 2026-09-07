import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { annotationComparison as initial } from '@/test/fixtures.comparisons';
import { relationshipRevision } from '@/test/fixtures.relationships';
import { identityRevision } from '@/test/fixtures.identities';
import { AnnotationComparisonResult } from './AnnotationComparisonResult';
it('displays exact revisions, frozen method differences and side-specific evidence anchors', async () => {
  render(<AnnotationComparisonResult value={initial} />);
  expect(screen.getByText(/selected before and selected after describe/i)).toHaveTextContent(
    'not inferred chronology',
  );
  expect(screen.getByText('Withdrawn after checking a counter-source.')).toBeInTheDocument();
  expect(
    screen.getByText(/Both support inputs and recorded confidence differ/),
  ).toBeInTheDocument();
  const confidence = screen.getByRole('region', { name: 'Confidence explanations' });
  await userEvent.click(
    within(confidence).getAllByText('Frozen source grades and independence groups')[0]!,
  );
  expect(
    within(confidence).getAllByText(/Reliability B; information credibility 2/)[0],
  ).toBeVisible();
  expect(within(confidence).getByText('Method: another-frozen-method')).toBeInTheDocument();
  expect(
    screen.getAllByRole('link', { name: 'Before: view evidence E1 in version 1' })[0],
  ).toHaveAttribute('href', `/reports/${initial.before.report_id}?version=1#evidence-E1`);
  expect(
    screen.getAllByRole('link', { name: 'After: view evidence E1 in version 2' })[0],
  ).toHaveAttribute('href', `/reports/${initial.after.report_id}?version=2#evidence-E1`);
});
it('renders distinct roots and unmatched judgements separately, without turning absence into withdrawal', () => {
  render(
    <AnnotationComparisonResult
      value={{
        ...initial,
        before: {
          ...initial.before,
          revisions: [],
          identity_revisions: [identityRevision],
          relationship_revisions: [relationshipRevision],
        },
        after: {
          ...initial.after,
          revisions: [],
          assessment: null,
          judgements: [
            {
              ...initial.after.judgements[0]!,
              statement: 'A different statement with the reused label.',
            },
          ],
        },
        annotation_changes: [
          {
            kind: 'identity',
            before_revision_id: identityRevision.id,
            after_revision_id: null,
            correspondence: 'unmatched',
            status: 'removed',
            changed_fields: [],
          },
          {
            kind: 'relationship',
            before_revision_id: relationshipRevision.id,
            after_revision_id: null,
            correspondence: 'unmatched',
            status: 'removed',
            changed_fields: [],
          },
        ],
        confidence_changes: [
          {
            before_judgement_id: 'KJ1',
            after_judgement_id: null,
            correspondence: 'unmatched',
            status: 'removed',
            changed_fields: [],
            explanations: ['Reused labels do not establish correspondence.'],
          },
          {
            before_judgement_id: null,
            after_judgement_id: 'KJ1',
            correspondence: 'unmatched',
            status: 'added',
            changed_fields: [],
            explanations: [],
          },
        ],
      }}
    />,
  );
  expect(screen.getAllByText('Separate, unmatched judgement')).toHaveLength(2);
  expect(screen.getAllByText(/no revision selected. This is not a withdrawal/)).toHaveLength(2);
  expect(screen.getByText(/Frozen assessment unavailable/)).toBeInTheDocument();
  expect(screen.getByText(/accounting-consolidation parent, not an ownership/)).toBeInTheDocument();
});
it('presents empty comparisons and inert untrusted declarations honestly', () => {
  render(
    <AnnotationComparisonResult
      value={{
        ...initial,
        annotation_changes: [],
        confidence_changes: [],
        evidence_changes: [],
        correspondences: [
          {
            kind: 'claim',
            before_revision_id: 'a',
            after_revision_id: 'b',
            rationale: '<script>not executable</script>',
          },
        ],
      }}
    />,
  );
  expect(screen.getByText('No annotation revisions selected.')).toBeInTheDocument();
  expect(screen.getByText('No judgement assessments to compare.')).toBeInTheDocument();
  expect(screen.getByText('No evidence differences recorded.')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  expect(screen.getByText('<script>not executable</script>')).toBeInTheDocument();
});
